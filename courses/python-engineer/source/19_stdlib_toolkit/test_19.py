from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from courselib import impl

m = impl("19")


class TestSafeJoin:
    def test_normal_join(self, tmp_path: Path):
        assert m.safe_join(tmp_path, "reports", "q1.csv") == (tmp_path / "reports/q1.csv").resolve()

    def test_single_part(self, tmp_path: Path):
        assert m.safe_join(tmp_path, "file.txt").name == "file.txt"

    @pytest.mark.parametrize(
        "parts",
        [("..",), ("../..", "etc", "passwd"), ("reports", "..", "..", "secrets"), ("/etc/passwd",)],
    )
    def test_escape_attempts_raise(self, tmp_path: Path, parts):
        with pytest.raises(ValueError, match="escapes root"):
            m.safe_join(tmp_path, *parts)

    def test_inner_dotdot_that_stays_inside_is_allowed(self, tmp_path: Path):
        assert m.safe_join(tmp_path, "a", "..", "b").name == "b"

    def test_symlink_out_is_rejected(self, tmp_path: Path):
        outside = tmp_path.parent / "outside_target"
        outside.mkdir(exist_ok=True)
        root = tmp_path / "root"
        root.mkdir()
        (root / "link").symlink_to(outside)
        with pytest.raises(ValueError):
            m.safe_join(root, "link")


class TestIterSourceFiles:
    @pytest.fixture
    def tree(self, tmp_path: Path) -> Path:
        (tmp_path / "pkg" / "sub").mkdir(parents=True)
        (tmp_path / ".venv" / "lib").mkdir(parents=True)
        for rel in ["a.py", "pkg/b.py", "pkg/sub/c.py", "pkg/notes.txt", ".venv/lib/d.py"]:
            (tmp_path / rel).write_text("x", encoding="utf-8")
        return tmp_path

    def test_finds_files_recursively(self, tree):
        names = [p.name for p in m.iter_source_files(tree)]
        assert sorted(names) == ["a.py", "b.py", "c.py", "d.py"]

    def test_filters_by_suffix(self, tree):
        assert [p.name for p in m.iter_source_files(tree, suffix=".txt")] == ["notes.txt"]

    def test_prunes_excluded_directories(self, tree):
        names = [p.name for p in m.iter_source_files(tree, exclude_dirs=frozenset({".venv"}))]
        assert sorted(names) == ["a.py", "b.py", "c.py"]

    def test_yields_paths(self, tree):
        assert all(isinstance(p, Path) for p in m.iter_source_files(tree))

    def test_is_lazy(self, tree):
        result = m.iter_source_files(tree)
        assert next(iter(result)) is not None  # works without materialising everything
        assert not isinstance(result, list)

    def test_missing_root(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            list(m.iter_source_files(tmp_path / "nope"))

    def test_empty_tree(self, tmp_path: Path):
        assert list(m.iter_source_files(tmp_path)) == []


class TestParseTimestamp:
    def test_offset(self):
        got = m.parse_timestamp("2026-08-02T14:31:07+02:00")
        assert got == datetime(2026, 8, 2, 12, 31, 7, tzinfo=UTC)

    def test_result_is_utc(self):
        assert m.parse_timestamp("2026-08-02T14:31:07+02:00").tzinfo is UTC

    def test_zulu(self):
        assert m.parse_timestamp("2026-08-02T14:31:07Z").hour == 14

    def test_space_separator(self):
        assert m.parse_timestamp("2026-08-02 14:31:07+00:00").minute == 31

    def test_unix_timestamp(self):
        expected = datetime(2026, 1, 1, tzinfo=UTC)
        assert m.parse_timestamp(str(int(expected.timestamp()))) == expected

    def test_naive_is_rejected(self):
        with pytest.raises(ValueError, match="naive"):
            m.parse_timestamp("2026-08-02T14:31:07")

    @pytest.mark.parametrize("bad", ["", "   ", "not a date", "2026-13-45T99:99:99Z"])
    def test_invalid(self, bad):
        with pytest.raises(ValueError):
            m.parse_timestamp(bad)

    def test_round_trip_through_a_fixed_offset(self):
        source = datetime(2026, 3, 1, 9, tzinfo=timezone(timedelta(hours=-5)))
        assert m.parse_timestamp(source.isoformat()) == source


CSV_TEXT = """id,name,score,active,note
1,ada,9.5,true,hello
2,bob,7,no,
"""


class TestLoadRecords:
    @pytest.fixture
    def csv_path(self, tmp_path: Path) -> Path:
        path = tmp_path / "data.csv"
        path.write_text(CSV_TEXT, encoding="utf-8")
        return path

    def test_coerces_types(self, csv_path):
        rows = m.load_records(csv_path, {"id": int, "name": str, "score": float})
        assert rows[0] == {"id": 1, "name": "ada", "score": 9.5}
        assert isinstance(rows[1]["score"], float)

    def test_drops_unlisted_columns(self, csv_path):
        assert set(m.load_records(csv_path, {"id": int})[0]) == {"id"}

    def test_booleans(self, csv_path):
        rows = m.load_records(csv_path, {"active": bool})
        assert [r["active"] for r in rows] == [True, False]

    def test_empty_becomes_none(self, csv_path):
        assert m.load_records(csv_path, {"note": str})[1]["note"] is None

    def test_missing_column_raises(self, csv_path):
        with pytest.raises(ValueError, match="missing"):
            m.load_records(csv_path, {"nope": int})

    def test_bad_value_names_the_row_and_column(self, tmp_path: Path):
        path = tmp_path / "bad.csv"
        path.write_text("id\n1\nnotanumber\n", encoding="utf-8")
        with pytest.raises(ValueError) as info:
            m.load_records(path, {"id": int})
        assert "row 2" in str(info.value) and "id" in str(info.value)

    def test_empty_file_with_header(self, tmp_path: Path):
        path = tmp_path / "empty.csv"
        path.write_text("id,name\n", encoding="utf-8")
        assert m.load_records(path, {"id": int}) == []


class TestCanonicalHash:
    def test_key_order_does_not_matter(self):
        assert m.canonical_hash({"a": 1, "b": 2}) == m.canonical_hash({"b": 2, "a": 1})

    def test_nested_key_order(self):
        assert m.canonical_hash({"x": {"a": 1, "b": 2}}) == m.canonical_hash({"x": {"b": 2, "a": 1}})

    def test_list_order_does_matter(self):
        assert m.canonical_hash([1, 2]) != m.canonical_hash([2, 1])

    def test_different_values_differ(self):
        assert m.canonical_hash({"a": 1}) != m.canonical_hash({"a": 2})

    def test_is_a_sha256_hex_digest(self):
        digest = m.canonical_hash({"a": 1})
        assert len(digest) == 64
        int(digest, 16)

    def test_handles_non_json_types(self):
        assert m.canonical_hash({"when": datetime(2026, 1, 1, tzinfo=UTC)})

    def test_stable_across_calls(self):
        payload = {"z": [1, {"y": None}], "a": True}
        assert m.canonical_hash(payload) == m.canonical_hash(payload)


class TestCli:
    def test_defaults(self):
        args = m.build_parser().parse_args(["import", "src.csv"])
        assert args.command == "import"
        assert args.format == "csv"
        assert args.verbose is False
        assert args.config is None

    def test_global_flags(self):
        args = m.build_parser().parse_args(["-v", "--config", "/tmp/c.toml", "export", "out"])
        assert args.verbose is True
        assert args.config == Path("/tmp/c.toml")

    def test_export_options(self):
        args = m.build_parser().parse_args(["export", "out", "--limit", "5", "--format", "json"])
        assert (args.dest, args.limit, args.format) == ("out", 5, "json")

    def test_dry_run_flag(self):
        assert m.build_parser().parse_args(["import", "s", "--dry-run"]).dry_run is True

    def test_subcommand_required(self):
        with pytest.raises(SystemExit):
            m.build_parser().parse_args([])

    def test_invalid_format_rejected(self):
        with pytest.raises(SystemExit):
            m.build_parser().parse_args(["import", "s", "--format", "xml"])

    def test_prog_name(self):
        assert m.build_parser().prog == "datatool"

    def test_main_returns_zero(self):
        assert m.main(["import", "src.csv"]) == 0

    def test_main_usage_error_returns_two(self):
        assert m.main(["export", "out", "--limit", "-1"]) == 2

    def test_main_takes_argv_so_no_monkeypatching_is_needed(self):
        assert m.main(["export", "out"]) == 0

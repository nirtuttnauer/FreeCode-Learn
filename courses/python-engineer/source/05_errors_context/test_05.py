import time
from pathlib import Path

import pytest

from courselib import impl

m = impl("05")


class TestHierarchy:
    def test_everything_is_a_pipeline_error(self):
        for cls in (m.RetryableError, m.FatalError, m.ValidationError):
            assert issubclass(cls, m.PipelineError)

    def test_validation_is_fatal_not_retryable(self):
        assert issubclass(m.ValidationError, m.FatalError)
        assert not issubclass(m.ValidationError, m.RetryableError)

    def test_retryable_carries_retry_after(self):
        assert m.RetryableError("busy").retry_after is None
        assert m.RetryableError("busy", 2.5).retry_after == 2.5
        assert str(m.RetryableError("busy")) == "busy"

    def test_validation_error_shape(self):
        err = m.ValidationError("port", "must be an integer")
        assert err.field == "port"
        assert err.message == "must be an integer"
        assert str(err) == "port: must be an integer"

    def test_catchable_by_base(self):
        with pytest.raises(m.PipelineError):
            raise m.ValidationError("a", "b")


class TestParsePort:
    def test_happy_path(self):
        assert m.parse_port({"port": "8080"}) == 8080
        assert m.parse_port({"port": 80}) == 80

    def test_missing_key_chains_from_keyerror(self):
        with pytest.raises(m.FatalError, match="required") as info:
            m.parse_port({})
        assert isinstance(info.value.__cause__, KeyError)

    def test_bad_value_chains_from_valueerror(self):
        with pytest.raises(m.FatalError, match="integer") as info:
            m.parse_port({"port": "http"})
        assert isinstance(info.value.__cause__, ValueError)

    def test_out_of_range_has_no_cause(self):
        with pytest.raises(m.FatalError, match="range") as info:
            m.parse_port({"port": 70000})
        assert info.value.__cause__ is None

    def test_zero_is_out_of_range(self):
        with pytest.raises(m.FatalError, match="range"):
            m.parse_port({"port": 0})


class TestValidateRecord:
    def test_valid_record_returns_none(self):
        assert m.validate_record({"name": "ada", "age": 36, "email": "a@b.c"}) is None

    def test_reports_every_problem_at_once(self):
        with pytest.raises(ExceptionGroup) as info:
            m.validate_record({})
        assert len(info.value.exceptions) == 3
        assert {e.field for e in info.value.exceptions} == {"name", "age", "email"}

    def test_single_problem_still_a_group(self):
        with pytest.raises(ExceptionGroup) as info:
            m.validate_record({"name": "ada", "age": 1, "email": "nope"})
        assert len(info.value.exceptions) == 1
        assert info.value.exceptions[0].field == "email"

    def test_bool_is_not_a_valid_age(self):
        with pytest.raises(ExceptionGroup) as info:
            m.validate_record({"name": "ada", "age": True, "email": "a@b"})
        assert info.value.exceptions[0].field == "age"

    def test_negative_age_rejected(self):
        with pytest.raises(ExceptionGroup):
            m.validate_record({"name": "ada", "age": -1, "email": "a@b"})

    def test_blank_name_rejected(self):
        with pytest.raises(ExceptionGroup):
            m.validate_record({"name": "   ", "age": 1, "email": "a@b"})

    def test_except_star_can_filter(self):
        caught = []
        try:
            m.validate_record({})
        except* m.ValidationError as group:
            caught.extend(group.exceptions)
        assert len(caught) == 3


class TestTimer:
    def test_measures_elapsed(self):
        with m.Timer() as t:
            time.sleep(0.01)
        assert t.elapsed >= 0.005

    def test_elapsed_set_even_on_exception(self):
        timer = m.Timer()
        with pytest.raises(ValueError), timer:
            raise ValueError("boom")
        assert timer.elapsed >= 0

    def test_does_not_swallow(self):
        with pytest.raises(KeyError), m.Timer():
            raise KeyError("still raised")

    def test_elapsed_unavailable_before_exit(self):
        with m.Timer() as t, pytest.raises(AttributeError):
            _ = t.elapsed

    def test_repr(self):
        assert repr(m.Timer("load")) == "Timer('load')"

    def test_as_binds_the_timer(self):
        with m.Timer("x") as t:
            assert t.label == "x"


class TestSuppressAndCollect:
    def test_collects_and_suppresses(self):
        errors = []
        with m.suppress_and_collect(errors, ValueError):
            raise ValueError("caught")
        assert [str(e) for e in errors] == ["caught"]

    def test_unlisted_exception_propagates(self):
        errors = []
        with pytest.raises(KeyError), m.suppress_and_collect(errors, ValueError):
            raise KeyError("nope")
        assert errors == []

    def test_no_exception_leaves_sink_empty(self):
        errors = []
        with m.suppress_and_collect(errors, ValueError):
            pass
        assert errors == []

    def test_multiple_types(self):
        errors = []
        for exc in (ValueError("a"), TypeError("b")):
            with m.suppress_and_collect(errors, ValueError, TypeError):
                raise exc
        assert len(errors) == 2

    def test_no_types_suppresses_nothing(self):
        errors = []
        with pytest.raises(ValueError), m.suppress_and_collect(errors):
            raise ValueError

    def test_subclasses_match(self):
        errors = []
        with m.suppress_and_collect(errors, LookupError):
            raise KeyError("subclass of LookupError")
        assert len(errors) == 1


class TestAtomicWrite:
    def test_writes_content(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        with m.atomic_write(target) as fh:
            fh.write("hello")
        assert target.read_text() == "hello"

    def test_overwrites_existing(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        target.write_text("old")
        with m.atomic_write(target) as fh:
            fh.write("new")
        assert target.read_text() == "new"

    def test_original_survives_a_failed_write(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        target.write_text("original")
        with pytest.raises(RuntimeError), m.atomic_write(target) as fh:
            fh.write("partial")
            raise RuntimeError("crashed mid-write")
        assert target.read_text() == "original"

    def test_no_temp_files_left_on_success(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        with m.atomic_write(target) as fh:
            fh.write("x")
        assert [p.name for p in tmp_path.iterdir()] == ["out.txt"]

    def test_no_temp_files_left_on_failure(self, tmp_path: Path):
        target = tmp_path / "out.txt"
        target.write_text("original")
        with pytest.raises(RuntimeError), m.atomic_write(target) as fh:
            fh.write("x")
            raise RuntimeError
        assert [p.name for p in tmp_path.iterdir()] == ["out.txt"]

    def test_nothing_created_when_new_file_write_fails(self, tmp_path: Path):
        target = tmp_path / "never.txt"
        with pytest.raises(RuntimeError), m.atomic_write(target) as fh:
            fh.write("x")
            raise RuntimeError
        assert not target.exists()
        assert list(tmp_path.iterdir()) == []

    def test_unicode_roundtrip(self, tmp_path: Path):
        target = tmp_path / "u.txt"
        with m.atomic_write(target) as fh:
            fh.write("héllo → wörld")
        assert target.read_text(encoding="utf-8") == "héllo → wörld"

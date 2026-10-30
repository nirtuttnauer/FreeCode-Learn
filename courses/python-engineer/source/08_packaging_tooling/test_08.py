import sys
from pathlib import Path

import pytest

from courselib import impl

m = impl("08")


class TestPackageVersion:
    def test_installed_package(self):
        assert m.package_version("pytest")[0].isdigit()

    def test_missing_package_uses_fallback(self):
        assert m.package_version("definitely-not-a-real-package-xyz") == "0.0.0+dev"

    def test_custom_fallback(self):
        assert m.package_version("nope-not-real-xyz", "1.2.3") == "1.2.3"


class TestLoadObject:
    def test_class(self):
        assert m.load_object("collections:OrderedDict").__name__ == "OrderedDict"

    def test_function(self):
        assert m.load_object("json:dumps")({"a": 1}) == '{"a": 1}'

    def test_dotted_submodule(self):
        assert m.load_object("os.path:join")("a", "b").endswith("b")

    def test_dotted_attribute(self):
        assert m.load_object("collections:OrderedDict.fromkeys")("ab") == {"a": None, "b": None}

    def test_missing_colon(self):
        with pytest.raises(ValueError, match="module:attribute"):
            m.load_object("json.dumps")

    def test_empty_parts(self):
        with pytest.raises(ValueError):
            m.load_object("json:")

    def test_unimportable_module(self):
        with pytest.raises(ImportError):
            m.load_object("no_such_module_xyz:thing")

    def test_missing_attribute(self):
        with pytest.raises(AttributeError):
            m.load_object("json:no_such_function")


class TestFindProjectRoot:
    def test_finds_the_course_root(self):
        root = m.find_project_root(Path(__file__))
        assert (root / "pyproject.toml").exists()
        assert (root / "courselib.py").exists()

    def test_accepts_a_directory(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").touch()
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        assert m.find_project_root(nested) == tmp_path

    def test_returns_start_when_marker_is_there(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").touch()
        assert m.find_project_root(tmp_path) == tmp_path

    def test_custom_marker(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "src"
        nested.mkdir()
        assert m.find_project_root(nested, marker=".git") == tmp_path

    def test_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            m.find_project_root(tmp_path, marker="definitely-not-here.toml")


PYPROJECT = """
[project]
name = "demo"
dependencies = ["httpx>=0.27", "rich"]

[project.optional-dependencies]
dev = ["pytest"]
docs = []
"""


class TestReadDependencies:
    @pytest.fixture
    def toml(self, tmp_path: Path) -> Path:
        path = tmp_path / "pyproject.toml"
        path.write_text(PYPROJECT)
        return path

    def test_main_dependencies(self, toml):
        assert m.read_dependencies(toml) == ["httpx>=0.27", "rich"]

    def test_extra(self, toml):
        assert m.read_dependencies(toml, "dev") == ["pytest"]

    def test_empty_extra(self, toml):
        assert m.read_dependencies(toml, "docs") == []

    def test_unknown_extra_raises(self, toml):
        with pytest.raises(KeyError):
            m.read_dependencies(toml, "nope")

    def test_missing_sections_return_empty(self, tmp_path: Path):
        path = tmp_path / "pyproject.toml"
        path.write_text("[tool.ruff]\nline-length = 100\n")
        assert m.read_dependencies(path) == []

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            m.read_dependencies(tmp_path / "nope.toml")

    def test_reads_the_courses_own_pyproject(self):
        root = m.find_project_root(Path(__file__))
        assert "pytest>=8.0" in m.read_dependencies(root / "pyproject.toml", "dev")


class TestLazyImport:
    def test_does_not_import_eagerly(self):
        sys.modules.pop("wave", None)  # a stdlib module nothing else here imports
        proxy = m.lazy_import("wave")
        assert "wave" not in sys.modules
        assert callable(proxy.open)
        assert "wave" in sys.modules

    def test_attribute_access_works(self):
        proxy = m.lazy_import("json")
        assert proxy.dumps({"a": 1}) == '{"a": 1}'

    def test_imports_only_once(self):
        proxy = m.lazy_import("json")
        assert proxy.dumps is proxy.dumps

    def test_repr_reflects_state(self):
        sys.modules.pop("colorsys", None)
        proxy = m.lazy_import("colorsys")
        assert repr(proxy) == "<lazy module 'colorsys' (not loaded)>"
        proxy.rgb_to_hls
        assert repr(proxy) == "<lazy module 'colorsys' (loaded)>"

    def test_bad_module_fails_on_access_not_creation(self):
        proxy = m.lazy_import("no_such_module_xyz")  # no error here
        with pytest.raises(ImportError):
            proxy.anything

    def test_missing_attribute_raises(self):
        with pytest.raises(AttributeError):
            m.lazy_import("json").no_such_attr

    def test_dir_works(self):
        assert "dumps" in dir(m.lazy_import("json"))

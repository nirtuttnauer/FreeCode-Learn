import copy

import pytest

from courselib import impl

m = impl("04b")
Pipeline, FrozenBox = m.Pipeline, m.FrozenBox
CountingDict, Interval, Recorder = m.CountingDict, m.Interval, m.Recorder


def strip(s):
    return s.strip()


def upper(s):
    return s.upper()


def exclaim(s):
    return s + "!"


class TestPipeline:
    def test_calls_left_to_right(self):
        assert Pipeline(strip, upper)("  hi  ") == "HI"

    def test_empty_pipeline_is_identity(self):
        assert Pipeline()(7) == 7

    def test_or_appends(self):
        p = Pipeline(strip) | upper
        assert p("  hi  ") == "HI"

    def test_ror_prepends(self):
        p = strip | Pipeline(upper)
        assert p("  hi  ") == "HI"
        assert [s.__name__ for s in p.steps] == ["strip", "upper"]

    def test_pipeline_or_pipeline(self):
        p = Pipeline(strip) | Pipeline(upper, exclaim)
        assert p("  hi ") == "HI!"
        assert len(p) == 3

    def test_or_does_not_mutate(self):
        base = Pipeline(strip)
        base | upper
        assert len(base) == 1

    def test_len_and_truthiness(self):
        assert len(Pipeline(strip, upper)) == 2
        assert not Pipeline()
        assert Pipeline(strip)

    def test_repr(self):
        assert repr(Pipeline(strip, upper)) == "Pipeline(strip, upper)"
        assert repr(Pipeline()) == "Pipeline()"

    def test_callable(self):
        assert callable(Pipeline())


class TestFrozenBox:
    def test_attribute_and_item_access(self):
        box = FrozenBox({"host": "x", "port": 1})
        assert box.host == "x"
        assert box["port"] == 1

    def test_nested_dicts_are_boxed(self):
        box = FrozenBox({"db": {"port": 5432}})
        assert isinstance(box.db, FrozenBox)
        assert box.db.port == 5432

    def test_missing_attribute_raises_attributeerror(self):
        with pytest.raises(AttributeError):
            FrozenBox({}).nope

    def test_missing_key_raises_keyerror(self):
        with pytest.raises(KeyError):
            FrozenBox({})["nope"]

    def test_hasattr_works(self):
        box = FrozenBox({"a": 1})
        assert hasattr(box, "a")
        assert not hasattr(box, "b")

    def test_immutable(self):
        box = FrozenBox({"a": 1})
        with pytest.raises(AttributeError):
            box.a = 2
        with pytest.raises(AttributeError):
            box.b = 2
        with pytest.raises(AttributeError):
            del box.a
        with pytest.raises(TypeError):
            box["a"] = 2

    def test_container_protocol(self):
        box = FrozenBox({"a": 1, "b": 2})
        assert len(box) == 2
        assert "a" in box
        assert "z" not in box
        assert sorted(box) == ["a", "b"]

    def test_dir_includes_keys(self):
        assert "host" in dir(FrozenBox({"host": "x"}))

    def test_equality(self):
        assert FrozenBox({"a": 1}) == FrozenBox({"a": 1})
        assert FrozenBox({"a": 1}) == {"a": 1}
        assert FrozenBox({"a": 1}) != {"a": 2}
        assert FrozenBox({"db": {"a": 1}}) == {"db": {"a": 1}}

    def test_repr(self):
        assert repr(FrozenBox({"a": 1})) == "FrozenBox({'a': 1})"

    def test_empty_construction(self):
        assert len(FrozenBox()) == 0

    def test_deepcopy_still_works(self):
        # This is what breaks when __getattr__ fakes dunder attributes.
        box = FrozenBox({"a": 1})
        assert copy.deepcopy(box) == box


class TestCountingDict:
    def test_missing_key_uses_factory(self):
        d = CountingDict(lambda: 0)
        assert d["absent"] == 0

    def test_missing_key_is_stored(self):
        d = CountingDict(list)
        d["x"].append(1)
        assert d["x"] == [1]
        assert "x" in d

    def test_counts_misses(self):
        d = CountingDict(lambda: 0)
        assert d.misses == 0
        d["a"], d["b"], d["a"]
        assert d.misses == 2  # "a" is only a miss the first time

    def test_get_does_not_trigger_missing(self):
        d = CountingDict(lambda: 0)
        assert d.get("nope") is None
        assert d.misses == 0
        assert len(d) == 0

    def test_initial_data_is_not_a_miss(self):
        d = CountingDict(lambda: 0, {"a": 1})
        assert d["a"] == 1
        assert d.misses == 0

    def test_kwargs_construction(self):
        d = CountingDict(lambda: 0, a=1)
        assert d["a"] == 1

    def test_misses_is_not_a_key(self):
        d = CountingDict(lambda: 0)
        d["x"]
        assert list(d) == ["x"]

    def test_is_a_real_dict(self):
        assert isinstance(CountingDict(lambda: 0), dict)


class TestInterval:
    def test_membership_is_half_open(self):
        i = Interval(1, 5)
        assert 1 in i
        assert 4.999 in i
        assert 5 not in i
        assert 0 not in i

    def test_truthiness(self):
        assert Interval(1, 5)
        assert not Interval(5, 5)
        assert not Interval(5, 1)

    def test_length(self):
        assert Interval(1, 5).length == 4
        assert Interval(5, 1).length == 0

    def test_intersection(self):
        assert Interval(1, 5) & Interval(3, 9) == Interval(3, 5)

    def test_disjoint_intersection_is_empty(self):
        assert not (Interval(1, 2) & Interval(5, 6))

    def test_union_of_overlapping(self):
        assert Interval(1, 5) | Interval(3, 9) == Interval(1, 9)

    def test_union_of_adjacent(self):
        assert Interval(1, 5) | Interval(5, 9) == Interval(1, 9)

    def test_union_of_disjoint_raises(self):
        with pytest.raises(ValueError):
            Interval(1, 2) | Interval(5, 6)

    def test_str_and_format(self):
        i = Interval(1, 5)
        assert str(i) == "[1, 5)"
        assert f"{i:.2f}" == "[1.00, 5.00)"
        assert repr(i) == "Interval(1, 5)"

    def test_hashable(self):
        assert len({Interval(1, 5), Interval(1, 5), Interval(2, 3)}) == 2

    def test_non_numeric_membership_is_false(self):
        assert "x" not in Interval(1, 5)


class TestRecorder:
    def test_records_calls(self):
        r = Recorder()
        r.save(1, mode="w")
        assert r.calls == [("save", (1,), {"mode": "w"})]

    def test_returns_none(self):
        r = Recorder()
        assert r.anything() is None

    def test_multiple_calls(self):
        r = Recorder()
        r.a()
        r.b(1)
        r.a(2)
        assert [c[0] for c in r.calls] == ["a", "b", "a"]

    def test_calls_is_a_real_list(self):
        r = Recorder()
        assert isinstance(r.calls, list)

    def test_underscore_names_raise(self):
        r = Recorder()
        with pytest.raises(AttributeError):
            r._private
        with pytest.raises(AttributeError):
            r.__deepcopy__

    def test_copy_still_works(self):
        r = Recorder()
        r.ping()
        assert len(copy.deepcopy(r)) == 1

    def test_was_called(self):
        r = Recorder()
        r.save()
        assert r.was_called("save")
        assert not r.was_called("load")

    def test_len_and_repr(self):
        r = Recorder()
        assert repr(r) == "Recorder(0 calls)"
        r.a()
        assert repr(r) == "Recorder(1 call)"
        r.b()
        assert repr(r) == "Recorder(2 calls)" and len(r) == 2

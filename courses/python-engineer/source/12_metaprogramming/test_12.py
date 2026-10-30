import pytest

from courselib import impl

m = impl("12")


class TestValidated:
    @pytest.fixture
    def Order(self):
        class Order:
            quantity = m.Validated(int, lambda v: v > 0, "must be positive")
            label = m.Validated(str)

        return Order

    def test_accepts_valid_values(self, Order):
        o = Order()
        o.quantity = 5
        o.label = "widgets"
        assert (o.quantity, o.label) == (5, "widgets")

    def test_type_error(self, Order):
        with pytest.raises(TypeError, match="quantity must be int"):
            Order().quantity = "five"

    def test_predicate_error(self, Order):
        with pytest.raises(ValueError, match="quantity must be positive"):
            Order().quantity = 0

    def test_no_predicate_means_type_only(self, Order):
        o = Order()
        o.label = ""
        assert o.label == ""

    def test_unset_attribute(self, Order):
        with pytest.raises(AttributeError, match="quantity is not set"):
            Order().quantity

    def test_fields_are_independent(self, Order):
        a, b = Order(), Order()
        a.quantity = 1
        b.quantity = 2
        assert (a.quantity, b.quantity) == (1, 2)

    def test_two_descriptors_do_not_collide(self, Order):
        o = Order()
        o.quantity = 7
        o.label = "x"
        assert o.quantity == 7

    def test_class_access_returns_the_descriptor(self, Order):
        assert isinstance(Order.quantity, m.Validated)

    def test_is_a_data_descriptor(self, Order):
        o = Order()
        o.quantity = 5
        o.__dict__["quantity"] = 999  # poking the instance dict directly
        assert o.quantity == 5  # the data descriptor still wins

    def test_delete(self, Order):
        o = Order()
        o.quantity = 5
        del o.quantity
        with pytest.raises(AttributeError):
            o.quantity


class TestRegistry:
    @pytest.fixture(autouse=True)
    def isolated_registry(self):
        saved = dict(m.Registry.registry)
        m.Registry.registry.clear()
        yield
        m.Registry.registry.clear()
        m.Registry.registry.update(saved)

    def test_registers_by_lowercased_name(self):
        class JsonHandler(m.Registry):
            pass

        assert m.Registry.registry["jsonhandler"] is JsonHandler

    def test_explicit_key(self):
        class Csv(m.Registry, key="csv"):
            pass

        assert m.Registry.get("csv") is Csv

    def test_duplicate_key_raises(self):
        class First(m.Registry, key="dup"):
            pass

        with pytest.raises(ValueError, match="dup"):

            class Second(m.Registry, key="dup"):
                pass

    def test_abstract_skips_registration(self):
        class Base(m.Registry, abstract=True):
            pass

        assert m.Registry.registry == {}

    def test_grandchildren_register(self):
        class Base(m.Registry, abstract=True):
            pass

        class Child(Base, key="child"):
            pass

        assert m.Registry.get("child") is Child

    def test_unknown_key_lists_known_ones(self):
        class Csv(m.Registry, key="csv"):
            pass

        with pytest.raises(KeyError) as info:
            m.Registry.get("nope")
        assert "csv" in str(info.value)

    def test_cooperates_with_other_hooks(self):
        seen = []

        class Mixin:
            def __init_subclass__(cls, **kwargs):
                super().__init_subclass__(**kwargs)
                seen.append(cls.__name__)

        class Combined(m.Registry, Mixin, key="combined"):
            pass

        assert seen == ["Combined"]  # our hook called super(), so the mixin's ran too


class TestAutoSlots:
    def test_creates_slots(self):
        @m.auto_slots
        class Point:
            x: int
            y: int

        assert Point.__slots__ == ("x", "y")

    def test_no_instance_dict(self):
        @m.auto_slots
        class Point:
            x: int

        p = Point()
        p.x = 1
        assert not hasattr(p, "__dict__")
        with pytest.raises(AttributeError):
            p.z = 3

    def test_methods_survive(self):
        @m.auto_slots
        class Point:
            x: int

            def double(self):
                return self.x * 2

        p = Point()
        p.x = 21
        assert p.double() == 42

    def test_class_attributes_are_not_slotted(self):
        @m.auto_slots
        class Config:
            name: str
            version: int = 1  # has a value, so it stays a class attribute

        assert Config.__slots__ == ("name",)
        assert Config.version == 1

    def test_preserves_metadata(self):
        @m.auto_slots
        class Documented:
            """My docstring."""

            x: int

        assert Documented.__doc__ == "My docstring."
        assert Documented.__name__ == "Documented"

    def test_no_annotations(self):
        @m.auto_slots
        class Empty:
            pass

        assert Empty.__slots__ == ()


class TestCallLogger:
    def test_logs_calls(self):
        log = []

        @m.call_logger(log)
        class Service:
            def run(self, n):
                return n * 2

        assert Service().run(2) == 4
        assert log == ["run(2)"]

    def test_kwargs_rendering(self):
        log = []

        @m.call_logger(log)
        class Service:
            def run(self, a, b=0):
                return a + b

        Service().run(1, b=2)
        assert log == ["run(1, b=2)"]

    def test_private_methods_are_skipped(self):
        log = []

        @m.call_logger(log)
        class Service:
            def _internal(self):
                return 1

            def __init__(self):
                pass

        Service()._internal()
        assert log == []

    def test_exceptions_pass_through_and_are_logged(self):
        log = []

        @m.call_logger(log)
        class Service:
            def boom(self):
                raise ValueError

        with pytest.raises(ValueError):
            Service().boom()
        assert log == ["boom()"]

    def test_metadata_preserved(self):
        log = []

        @m.call_logger(log)
        class Service:
            def documented(self):
                """Docs."""

        assert Service.documented.__name__ == "documented"
        assert Service.documented.__doc__ == "Docs."

    def test_each_method_logs_its_own_name(self):
        log = []

        @m.call_logger(log)
        class Service:
            def a(self):
                pass

            def b(self):
                pass

        s = Service()
        s.a()
        s.b()
        assert log == ["a()", "b()"]  # not ["b()", "b()"] — watch out for late binding


class TestBuildModel:
    @pytest.fixture
    def User(self):
        return m.build_model("User", {"id": int, "name": str})

    def test_construction_and_attributes(self, User):
        u = User(id=1, name="ada")
        assert (u.id, u.name) == (1, "ada")

    def test_repr(self, User):
        assert repr(User(id=1, name="ada")) == "User(id=1, name='ada')"

    def test_class_name(self, User):
        assert User.__name__ == "User"

    def test_keyword_only(self, User):
        with pytest.raises(TypeError):
            User(1, "ada")

    def test_missing_field(self, User):
        with pytest.raises(TypeError, match="name"):
            User(id=1)

    def test_unknown_field(self, User):
        with pytest.raises(TypeError, match="admin"):
            User(id=1, name="a", admin=True)

    def test_type_validation(self, User):
        with pytest.raises(TypeError, match="id must be int"):
            User(id="one", name="ada")

    def test_equality_by_value(self, User):
        assert User(id=1, name="a") == User(id=1, name="a")
        assert User(id=1, name="a") != User(id=2, name="a")

    def test_different_models_are_not_equal(self, User):
        Other = m.build_model("User", {"id": int, "name": str})
        assert User(id=1, name="a") != Other(id=1, name="a")

    def test_hashable(self, User):
        assert len({User(id=1, name="a"), User(id=1, name="a")}) == 1

    def test_metadata(self, User):
        assert User.__annotations__ == {"id": int, "name": str}
        assert User._fields == ("id", "name")

    def test_independent_models(self):
        A = m.build_model("A", {"x": int})
        B = m.build_model("B", {"y": str})
        assert A(x=1).x == 1
        assert B(y="s").y == "s"

import math
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Decimal

import pytest

from courselib import impl

m = impl("04")
Point2D = m.Point2D
Rectangle = m.Rectangle
BankAccount = m.BankAccount
Multiplier = m.Multiplier
Playlist = m.Playlist
Color = m.Color
InventoryItem = m.InventoryItem
HighScore = m.HighScore
Percentage = m.Percentage
Employee = m.Employee
Person = m.Person
Shape = m.Shape
Circle = m.Circle
Square = m.Square
TagSet = m.TagSet
StepCounter = m.StepCounter
Money = m.Money
Temperature = m.Temperature
CircularBuffer = m.CircularBuffer
CaseInsensitiveDict = m.CaseInsensitiveDict


# =============================================================================
# Warmup tests
# =============================================================================


class TestPoint2D:
    def test_coordinates_accessible(self):
        p = Point2D(3, 4)
        assert p.x == 3
        assert p.y == 4

    def test_repr_and_str(self):
        p = Point2D(1, 2)
        assert repr(p) == "Point2D(1, 2)"
        assert str(p) == "(1, 2)"

    def test_equality(self):
        assert Point2D(1, 2) == Point2D(1, 2)
        assert Point2D(1, 2) != Point2D(1, 3)
        assert Point2D(1, 2) != (1, 2)

    def test_addition_and_subtraction(self):
        assert Point2D(1, 2) + Point2D(3, 4) == Point2D(4, 6)
        assert Point2D(5, 5) - Point2D(2, 1) == Point2D(3, 4)

    def test_add_sub_non_point_raises_type_error(self):
        with pytest.raises(TypeError):
            Point2D(1, 2) + (1, 2)
        with pytest.raises(TypeError):
            Point2D(1, 2) - 5

    def test_scalar_multiplication(self):
        assert Point2D(2, 3) * 3 == Point2D(6, 9)
        assert 2 * Point2D(2, 3) == Point2D(4, 6)
        assert Point2D(2, 4) * 0.5 == Point2D(1.0, 2.0)

    def test_abs(self):
        assert abs(Point2D(3, 4)) == pytest.approx(5.0)
        assert abs(Point2D(0, 0)) == 0.0


class TestRectangle:
    def test_dimensions_and_properties(self):
        r = Rectangle(4, 5)
        assert r.width == 4.0
        assert r.height == 5.0
        assert isinstance(r.width, float)
        assert isinstance(r.height, float)

    def test_area_and_perimeter(self):
        r = Rectangle(3, 4)
        assert r.area == 12.0
        assert r.perimeter == 14.0

    def test_setter_updates_values(self):
        r = Rectangle(2, 3)
        r.width = 5
        r.height = 10
        assert r.area == 50.0
        assert r.perimeter == 30.0

    def test_read_only_properties_raise_attribute_error(self):
        r = Rectangle(2, 3)
        with pytest.raises(AttributeError):
            r.area = 10
        with pytest.raises(AttributeError):
            r.perimeter = 20

    def test_validation_in_constructor(self):
        with pytest.raises(ValueError):
            Rectangle(-1, 5)
        with pytest.raises(ValueError):
            Rectangle(5, 0)

    def test_validation_in_setter(self):
        r = Rectangle(2, 3)
        with pytest.raises(ValueError):
            r.width = -10
        assert r.width == 2.0  # unchanged

    def test_repr(self):
        assert repr(Rectangle(4, 5)) == "Rectangle(width=4.0, height=5.0)"


class TestBankAccount:
    def test_init_defaults_and_owner(self):
        b = BankAccount("Alice")
        assert b.owner == "Alice"
        assert b.balance == 0.0

    def test_init_rejects_negative_balance(self):
        with pytest.raises(ValueError):
            BankAccount("Alice", -50)

    def test_deposit(self):
        b = BankAccount("Alice", 100)
        b.deposit(50)
        assert b.balance == 150.0

    def test_deposit_invalid_amount(self):
        b = BankAccount("Alice")
        with pytest.raises(ValueError):
            b.deposit(0)
        with pytest.raises(ValueError):
            b.deposit(-10)

    def test_withdraw(self):
        b = BankAccount("Alice", 100)
        b.withdraw(40)
        assert b.balance == 60.0

    def test_withdraw_insufficient_funds(self):
        b = BankAccount("Alice", 50)
        with pytest.raises(ValueError):
            b.withdraw(100)
        assert b.balance == 50.0

    def test_withdraw_invalid_amount(self):
        b = BankAccount("Alice", 50)
        with pytest.raises(ValueError):
            b.withdraw(0)
        with pytest.raises(ValueError):
            b.withdraw(-10)

    def test_str_and_repr(self):
        b = BankAccount("Alice", 123.45)
        assert str(b) == "$123.45 (Alice)"
        assert repr(b) == "BankAccount(owner='Alice', balance=123.45)"


class TestMultiplier:
    def test_callable(self):
        m = Multiplier(3)
        assert callable(m)
        assert m(10) == 30
        assert m(2.5) == 7.5

    def test_repr(self):
        assert repr(Multiplier(3)) == "Multiplier(factor=3)"


class TestPlaylist:
    def test_init_and_len(self):
        p = Playlist()
        assert len(p) == 0
        assert not p
        p2 = Playlist(["Song 1", "Song 2"])
        assert len(p2) == 2
        assert p2

    def test_add(self):
        p = Playlist()
        p.add("Song 1")
        assert len(p) == 1
        assert p[0] == "Song 1"

    def test_getitem_and_bounds(self):
        p = Playlist(["Song 1", "Song 2"])
        assert p[0] == "Song 1"
        assert p[-1] == "Song 2"
        with pytest.raises(IndexError):
            p[5]

    def test_iteration_and_contains(self):
        p = Playlist(["A", "B", "C"])
        assert list(p) == ["A", "B", "C"]
        assert "B" in p
        assert "Z" not in p

    def test_repr(self):
        assert repr(Playlist(["Song 1", "Song 2"])) == "Playlist(tracks=['Song 1', 'Song 2'])"


class TestColor:
    def test_valid_rgb(self):
        c = Color(255, 128, 0)
        assert c.r == 255
        assert c.g == 128
        assert c.b == 0

    def test_invalid_rgb_raises(self):
        for bad in [-1, 256, "red"]:
            with pytest.raises(ValueError):
                Color(bad, 0, 0)

    def test_hex_code(self):
        assert Color(255, 0, 0).hex_code == "#ff0000"
        assert Color(0, 255, 128).hex_code == "#00ff80"
        assert Color(0, 0, 0).hex_code == "#000000"

    def test_repr(self):
        assert repr(Color(255, 128, 0)) == "Color(r=255, g=128, b=0)"

    def test_equality_and_hash(self):
        assert Color(1, 2, 3) == Color(1, 2, 3)
        assert Color(1, 2, 3) != Color(1, 2, 4)
        assert len({Color(1, 2, 3), Color(1, 2, 3)}) == 1
        assert {Color(255, 0, 0): "red"}[Color(255, 0, 0)] == "red"


class TestInventoryItem:
    def test_dataclass_defaults(self):
        item = InventoryItem("Widget", 9.99)
        assert item.name == "Widget"
        assert item.unit_price == 9.99
        assert item.quantity == 0
        assert item.tags == []

    def test_total_value(self):
        item = InventoryItem("Widget", 10.0, 5)
        assert item.total_value() == 50.0

    def test_in_stock(self):
        assert InventoryItem("Widget", 1.0, 3).in_stock() is True
        assert InventoryItem("Widget", 1.0, 0).in_stock() is False

    def test_dataclass_generated_methods(self):
        assert is_dataclass(InventoryItem)
        assert repr(InventoryItem("A", 1.0)).startswith("InventoryItem(")
        assert InventoryItem("A", 1.0) == InventoryItem("A", 1.0)


class TestHighScore:
    def test_equality(self):
        assert HighScore("Alice", 100) == HighScore("Bob", 100)
        assert HighScore("Alice", 100) != HighScore("Alice", 90)

    def test_ordering(self):
        assert HighScore("Bob", 50) < HighScore("Alice", 100)
        assert HighScore("Alice", 100) > HighScore("Bob", 50)
        assert HighScore("Bob", 50) <= HighScore("Alice", 100)
        assert HighScore("Alice", 100) >= HighScore("Alice", 100)

    def test_sorting(self):
        scores = [HighScore("A", 30), HighScore("B", 10), HighScore("C", 20)]
        assert [s.score for s in sorted(scores)] == [10, 20, 30]

    def test_repr(self):
        assert repr(HighScore("Alice", 100)) == "HighScore(player='Alice', score=100)"


class TestPercentage:
    def test_float_conversion(self):
        p = Percentage(0.852)
        assert float(p) == pytest.approx(0.852)

    def test_str_default(self):
        p = Percentage(0.852)
        assert str(p) == "85.2%"

    def test_format_specifiers(self):
        p = Percentage(0.852)
        assert f"{p:.0f}" == "85%"
        assert f"{p:.2f}" == "85.20%"
        assert f"{p}" == "85.2%"

    def test_repr_and_equality(self):
        p1 = Percentage(0.5)
        p2 = Percentage(0.5)
        assert p1 == p2
        assert repr(p1) == "Percentage(0.5)"


class TestEmployee:
    def setup_method(self):
        Employee.count = 0

    def test_auto_increment_ids(self):
        e1 = Employee("Alice")
        e2 = Employee("Bob", "Finance")
        assert e1.id == 1
        assert e2.id == 2
        assert Employee.count == 2

    def test_attributes_and_repr(self):
        e = Employee("Alice", "Engineering")
        assert e.name == "Alice"
        assert e.department == "Engineering"
        assert repr(e) == "Employee(id=1, name='Alice', department='Engineering')"


class TestPerson:
    def test_full_name_property(self):
        p = Person("Ada", "Lovelace")
        assert p.full_name == "Ada Lovelace"

    def test_from_full_name_constructor(self):
        p = Person.from_full_name("Alan Turing")
        assert p.first_name == "Alan"
        assert p.last_name == "Turing"

    def test_from_full_name_invalid_raises(self):
        with pytest.raises(ValueError):
            Person.from_full_name("SingleName")

    def test_from_dict_constructor(self):
        p = Person.from_dict({"first_name": "Grace", "last_name": "Hopper"})
        assert p.first_name == "Grace"
        assert p.last_name == "Hopper"

    def test_equality_and_repr(self):
        assert Person("Ada", "Lovelace") == Person("Ada", "Lovelace")
        assert repr(Person("Ada", "Lovelace")) == "Person(first_name='Ada', last_name='Lovelace')"


class TestShapes:
    def test_inheritance(self):
        assert issubclass(Circle, Shape)
        assert issubclass(Square, Shape)
        assert isinstance(Circle(2), Shape)
        assert isinstance(Square(2), Shape)

    def test_circle(self):
        c = Circle(3.0)
        assert c.radius == 3.0
        assert c.area() == pytest.approx(math.pi * 9)
        assert c.perimeter() == pytest.approx(2 * math.pi * 3)
        assert repr(c) == "Circle(radius=3.0)"

    def test_circle_invalid_radius(self):
        with pytest.raises(ValueError):
            Circle(0)
        with pytest.raises(ValueError):
            Circle(-5)

    def test_square(self):
        s = Square(4.0)
        assert s.side == 4.0
        assert s.area() == 16.0
        assert s.perimeter() == 16.0
        assert repr(s) == "Square(side=4.0)"

    def test_square_invalid_side(self):
        with pytest.raises(ValueError):
            Square(0)
        with pytest.raises(ValueError):
            Square(-2)


class TestTagSet:
    def test_normalization_and_uniqueness(self):
        ts = TagSet([" Python ", "python", "DEV"])
        assert len(ts) == 2
        assert "python" in ts
        assert "dev" in ts

    def test_union_operator(self):
        ts1 = TagSet(["a", "b"])
        ts2 = TagSet(["b", "c"])
        union = ts1 | ts2
        assert len(union) == 3
        assert "a" in union and "c" in union

    def test_intersection_operator(self):
        ts1 = TagSet(["a", "b"])
        ts2 = TagSet(["b", "c"])
        inter = ts1 & ts2
        assert len(inter) == 1
        assert "b" in inter

    def test_difference_operator(self):
        ts1 = TagSet(["a", "b"])
        ts2 = TagSet(["b", "c"])
        diff = ts1 - ts2
        assert len(diff) == 1
        assert "a" in diff

    def test_equality(self):
        assert TagSet(["a", "b"]) == TagSet(["B", "A"])

    def test_repr(self):
        assert "TagSet(" in repr(TagSet(["a"]))


class TestStepCounter:
    def test_initial_steps(self):
        sc = StepCounter(100)
        assert sc.steps == 100
        assert int(sc) == 100
        assert bool(sc) is True

    def test_zero_steps(self):
        sc = StepCounter()
        assert sc.steps == 0
        assert bool(sc) is False

    def test_negative_initial_raises(self):
        with pytest.raises(ValueError):
            StepCounter(-1)

    def test_inplace_add(self):
        sc = StepCounter(50)
        sc += 30
        assert sc.steps == 80
        assert int(sc) == 80

    def test_invalid_increment_raises(self):
        sc = StepCounter(50)
        with pytest.raises(ValueError):
            sc += 0
        with pytest.raises(ValueError):
            sc += -10
        with pytest.raises(TypeError):
            sc += "10"

    def test_reset(self):
        sc = StepCounter(100)
        sc.reset()
        assert sc.steps == 0
        assert not sc

    def test_repr(self):
        assert repr(StepCounter(42)) == "StepCounter(steps=42)"


# =============================================================================
# Advanced tests
# =============================================================================


class TestMoney:
    def test_is_a_frozen_dataclass(self):
        assert is_dataclass(Money)
        with pytest.raises(FrozenInstanceError):
            Money(1).amount = 2

    @pytest.mark.parametrize("raw", [1, "1", Decimal(1), 1.0])
    def test_amount_is_always_decimal(self, raw):
        assert Money(raw).amount == Decimal(1)
        assert isinstance(Money(raw).amount, Decimal)

    def test_float_is_coerced_exactly(self):
        assert Money(0.1).amount == Decimal("0.1")

    def test_currency_validation(self):
        assert Money(1, "EUR").currency == "EUR"
        for bad in ["usd", "US", "USDD", "12A", ""]:
            with pytest.raises(ValueError):
                Money(1, bad)

    def test_addition_and_subtraction(self):
        assert Money("1.10") + Money("2.20") == Money("3.30")
        assert Money(5) - Money(3) == Money(2)

    def test_decimal_precision_is_exact(self):
        total = sum([Money("0.1")] * 3, Money(0))
        assert total == Money("0.3")

    def test_currency_mismatch_raises(self):
        with pytest.raises(ValueError):
            Money(1, "USD") + Money(1, "EUR")

    def test_adding_non_money_is_a_type_error(self):
        with pytest.raises(TypeError):
            Money(1) + 1

    def test_multiplication_both_ways(self):
        assert Money(2) * 3 == Money(6)
        assert 3 * Money(2) == Money(6)
        assert Money("1.5") * Decimal(2) == Money(3)

    def test_money_times_money_is_a_type_error(self):
        with pytest.raises(TypeError):
            Money(2) * Money(3)

    def test_negation_and_abs(self):
        assert -Money(5) == Money(-5)
        assert abs(Money(-5)) == Money(5)

    def test_ordering(self):
        assert Money(1) < Money(2)
        assert Money(2) >= Money(2)
        assert sorted([Money(3), Money(1), Money(2)]) == [Money(1), Money(2), Money(3)]

    def test_ordering_across_currencies_raises(self):
        with pytest.raises(ValueError):
            Money(1, "USD") < Money(2, "EUR")

    def test_hashable(self):
        assert len({Money(1), Money(1), Money(2)}) == 2
        assert {Money(1, "EUR"): "fee"}[Money(1, "EUR")] == "fee"

    def test_str_format(self):
        assert str(Money("1234.5")) == "1,234.50 USD"
        assert str(Money(0, "EUR")) == "0.00 EUR"

    def test_repr_is_the_dataclass_default(self):
        assert repr(Money(1)).startswith("Money(")


class TestTemperature:
    def test_basic(self):
        t = Temperature(25)
        assert t.celsius == 25.0
        assert t.fahrenheit == 77.0
        assert t.kelvin == pytest.approx(298.15)

    def test_validation_in_constructor(self):
        with pytest.raises(ValueError):
            Temperature(-300)

    def test_validation_in_setter(self):
        t = Temperature(0)
        with pytest.raises(ValueError):
            t.celsius = -300
        assert t.celsius == 0.0  # unchanged

    def test_fahrenheit_setter(self):
        t = Temperature(0)
        t.fahrenheit = 212
        assert t.celsius == pytest.approx(100)

    def test_fahrenheit_setter_validates(self):
        t = Temperature(0)
        with pytest.raises(ValueError):
            t.fahrenheit = -500

    def test_kelvin_is_read_only(self):
        t = Temperature(0)
        with pytest.raises(AttributeError):
            t.kelvin = 0

    def test_from_fahrenheit(self):
        assert Temperature.from_fahrenheit(212).celsius == pytest.approx(100)

    def test_from_fahrenheit_respects_subclasses(self):
        class Oven(Temperature):
            pass

        assert type(Oven.from_fahrenheit(212)) is Oven

    def test_repr(self):
        assert repr(Temperature(25)) == "Temperature(25.0)"

    def test_equality_and_hash(self):
        assert Temperature(25) == Temperature(25.0)
        assert len({Temperature(1), Temperature(1)}) == 1

    def test_int_input_becomes_float(self):
        assert isinstance(Temperature(25).celsius, float)


class TestCircularBuffer:
    def test_rejects_bad_capacity(self):
        with pytest.raises(ValueError):
            CircularBuffer(0)

    def test_append_and_len(self):
        buf = CircularBuffer(3)
        buf.append(1)
        buf.append(2)
        assert len(buf) == 2

    def test_append_returns_none_until_full(self):
        buf = CircularBuffer(2)
        assert buf.append(1) is None
        assert buf.append(2) is None

    def test_append_returns_evicted_item(self):
        buf = CircularBuffer(2)
        buf.extend([1, 2])
        assert buf.append(3) == 1
        assert list(buf) == [2, 3]

    def test_iteration_is_oldest_first(self):
        buf = CircularBuffer(3)
        buf.extend([1, 2, 3, 4])
        assert list(buf) == [2, 3, 4]

    def test_indexing(self):
        buf = CircularBuffer(3)
        buf.extend([1, 2, 3])
        assert buf[0] == 1
        assert buf[-1] == 3

    def test_index_error(self):
        buf = CircularBuffer(3)
        buf.append(1)
        with pytest.raises(IndexError):
            buf[5]

    def test_contains(self):
        buf = CircularBuffer(2)
        buf.extend([1, 2, 3])
        assert 3 in buf
        assert 1 not in buf

    def test_full_property(self):
        buf = CircularBuffer(2)
        assert not buf.full
        buf.extend([1, 2])
        assert buf.full

    def test_truthiness_follows_len(self):
        buf = CircularBuffer(2)
        assert not buf
        buf.append(1)
        assert buf

    def test_repr(self):
        buf = CircularBuffer(3)
        buf.extend([1, 2, 3])
        assert repr(buf) == "CircularBuffer(capacity=3, items=[1, 2, 3])"


class TestCaseInsensitiveDict:
    def test_case_insensitive_lookup(self):
        d = CaseInsensitiveDict({"Content-Type": "json"})
        assert d["content-type"] == "json"
        assert d["CONTENT-TYPE"] == "json"

    def test_construction_forms(self):
        assert CaseInsensitiveDict({"A": 1})["a"] == 1
        assert CaseInsensitiveDict(a=1)["A"] == 1
        assert CaseInsensitiveDict({"A": 1}, b=2)["B"] == 2
        assert len(CaseInsensitiveDict()) == 0

    def test_remembers_latest_casing(self):
        d = CaseInsensitiveDict({"key": 1})
        d["KEY"] = 2
        assert list(d) == ["KEY"]
        assert len(d) == 1
        assert d["Key"] == 2

    def test_delete(self):
        d = CaseInsensitiveDict({"A": 1})
        del d["a"]
        assert len(d) == 0

    def test_missing_key_raises(self):
        with pytest.raises(KeyError):
            CaseInsensitiveDict()["nope"]

    def test_free_mutablemapping_methods(self):
        d = CaseInsensitiveDict({"A": 1})
        assert d.get("a") == 1
        assert d.get("zz", "default") == "default"
        assert "A" in d and "a" in d
        assert list(d.items()) == [("A", 1)]
        assert list(d.keys()) == ["A"]
        assert list(d.values()) == [1]
        d.setdefault("b", 2)
        assert d["B"] == 2
        assert d.pop("a") == 1
        d.update({"C": 3})
        assert d["c"] == 3

    def test_equality_ignores_case(self):
        assert CaseInsensitiveDict({"A": 1}) == CaseInsensitiveDict({"a": 1})
        assert CaseInsensitiveDict({"A": 1}) == {"a": 1}
        assert CaseInsensitiveDict({"A": 1}) != {"a": 2}
        assert CaseInsensitiveDict({"A": 1}) != {"a": 1, "b": 2}

    def test_repr(self):
        assert repr(CaseInsensitiveDict({"A": 1})) == "CaseInsensitiveDict({'A': 1})"

    def test_is_a_mutablemapping(self):
        from collections.abc import MutableMapping

        assert isinstance(CaseInsensitiveDict(), MutableMapping)

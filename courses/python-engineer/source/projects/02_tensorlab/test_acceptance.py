"""Acceptance tests for tensorlab, milestone 1 (the scalar engine).

Run: pytest projects/02_tensorlab -o addopts=""

Later milestones get their own tests — write them yourself as you go. These are the floor.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))

tensorlab = pytest.importorskip("tensorlab")
Value = tensorlab.Value


class TestForward:
    def test_construction(self):
        v = Value(2.0)
        assert v.data == 2.0
        assert v.grad == 0.0

    def test_int_is_coerced_to_float(self):
        assert isinstance(Value(2).data, float)

    def test_arithmetic(self):
        a, b = Value(2.0), Value(-3.0)
        assert (a + b).data == -1.0
        assert (a * b).data == -6.0
        assert (a - b).data == 5.0
        assert (a / b).data == pytest.approx(-2 / 3)
        assert (a**3).data == 8.0
        assert (-a).data == -2.0

    def test_mixing_with_plain_numbers(self):
        a = Value(2.0)
        assert (a + 1).data == 3.0
        assert (1 + a).data == 3.0
        assert (2 * a).data == 4.0
        assert (1 - a).data == -1.0
        assert (4 / a).data == 2.0

    def test_activations(self):
        assert Value(-2.0).relu().data == 0.0
        assert Value(3.0).relu().data == 3.0
        assert Value(0.0).tanh().data == 0.0
        assert Value(1.0).exp().data == pytest.approx(math.e)
        assert Value(math.e).log().data == pytest.approx(1.0)
        assert Value(0.0).sigmoid().data == pytest.approx(0.5)

    def test_log_of_nonpositive_raises(self):
        with pytest.raises(ValueError):
            Value(0.0).log()

    def test_repr(self):
        assert repr(Value(2.0)) == "Value(data=2.0, grad=0.0)"

    def test_ordering(self):
        assert sorted([Value(3), Value(1)], key=lambda v: v.data)[0].data == 1.0
        assert Value(1) < Value(2)


class TestBackward:
    def test_simple_chain(self):
        a, b = Value(2.0), Value(-3.0)
        c = a * b + a**2
        c.backward()
        assert a.grad == pytest.approx(-3.0 + 2 * 2.0)
        assert b.grad == pytest.approx(2.0)

    def test_gradients_accumulate_for_reused_nodes(self):
        # The classic bug: `=` instead of `+=` gives 2.0 here instead of 4.0.
        a = Value(2.0)
        (a * a).backward()
        assert a.grad == pytest.approx(4.0)

    def test_reuse_across_a_deeper_graph(self):
        a = Value(3.0)
        b = a + a + a  # db/da = 3
        b.backward()
        assert a.grad == pytest.approx(3.0)

    def test_relu_gradient_is_gated(self):
        positive, negative = Value(2.0), Value(-2.0)
        positive.relu().backward()
        negative.relu().backward()
        assert positive.grad == 1.0
        assert negative.grad == 0.0

    def test_tanh_gradient(self):
        x = Value(0.5)
        x.tanh().backward()
        assert x.grad == pytest.approx(1 - math.tanh(0.5) ** 2)

    def test_exp_gradient(self):
        x = Value(1.5)
        x.exp().backward()
        assert x.grad == pytest.approx(math.exp(1.5))

    def test_sigmoid_gradient(self):
        x = Value(0.3)
        x.sigmoid().backward()
        s = 1 / (1 + math.exp(-0.3))
        assert x.grad == pytest.approx(s * (1 - s))

    def test_division_gradient(self):
        a, b = Value(6.0), Value(3.0)
        (a / b).backward()
        assert a.grad == pytest.approx(1 / 3)
        assert b.grad == pytest.approx(-6 / 9)

    def test_power_gradient(self):
        x = Value(3.0)
        (x**4).backward()
        assert x.grad == pytest.approx(4 * 3.0**3)

    def test_a_small_network(self):
        x1, x2 = Value(2.0), Value(0.0)
        w1, w2 = Value(-3.0), Value(1.0)
        bias = Value(6.8813735870195432)
        out = (x1 * w1 + x2 * w2 + bias).tanh()
        out.backward()
        assert out.data == pytest.approx(0.7071, abs=1e-4)
        assert x1.grad == pytest.approx(-1.5, abs=1e-3)
        assert w1.grad == pytest.approx(1.0, abs=1e-3)

    def test_deep_graph_does_not_blow_the_stack(self):
        # An iterative topological sort survives this; naive recursion does not.
        v = Value(1.0)
        acc = v
        for _ in range(5000):
            acc = acc + 1
        acc.backward()
        assert v.grad == pytest.approx(1.0)

    def test_zero_grad(self):
        a = Value(2.0)
        c = a * a
        c.backward()
        c.zero_grad()
        assert a.grad == 0.0 and c.grad == 0.0


class TestGradcheck:
    def test_passes_for_a_correct_graph(self):
        def f(a, b):
            return (a * b + a.tanh()) * b

        inputs = [Value(0.7), Value(-1.3)]
        assert tensorlab.engine.gradcheck(f, inputs) is True

    def test_polynomial(self):
        assert tensorlab.engine.gradcheck(lambda x: x**3 + 2 * x, [Value(1.7)]) is True

    def test_activation_chain(self):
        def f(x):
            return x.sigmoid().log() * x.relu()

        assert tensorlab.engine.gradcheck(f, [Value(1.2)]) is True

"""Milestone 1: the scalar autograd engine.

Everything in tensorlab rests on this file. Get it right and the rest is bookkeeping.

The idea in four lines:
  1. Every operation builds a node that remembers its inputs (`_prev`) and how to
     push a gradient back to them (`_backward`).
  2. `.backward()` topologically sorts the graph so a node is only visited after
     everything that depends on it.
  3. Walk that order in reverse, calling each `_backward`.
  4. Gradients ACCUMULATE (`+=`). A node used twice receives two contributions.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


class Value:
    """A scalar with a gradient and a memory of how it was computed."""

    __slots__ = ("data", "grad", "label", "_prev", "_op", "_backward")

    def __init__(
        self,
        data: float,
        _children: Iterable["Value"] = (),
        _op: str = "",
        label: str = "",
    ) -> None:
        self.data = float(data)
        self.grad = 0.0
        self.label = label
        self._prev: tuple[Value, ...] = tuple(_children)
        self._op = _op
        # Called during backprop to push this node's grad into its children.
        self._backward: Callable[[], None] = lambda: None

    # -- construction helpers ------------------------------------------------------------
    @staticmethod
    def _wrap(other: Any) -> "Value":
        """Turn a bare int/float into a Value so `2 * a` works. TODO."""
        raise NotImplementedError

    # -- arithmetic ----------------------------------------------------------------------
    # For each: compute the forward value, build the node, and define _backward using
    # the local derivative times `out.grad` (the chain rule).
    def __add__(self, other: Any) -> "Value":
        raise NotImplementedError

    def __mul__(self, other: Any) -> "Value":
        raise NotImplementedError

    def __pow__(self, exponent: float) -> "Value":
        """Only supports int/float exponents — d/dx x**n = n * x**(n-1)."""
        raise NotImplementedError

    def __neg__(self) -> "Value":
        raise NotImplementedError

    def __sub__(self, other: Any) -> "Value":
        raise NotImplementedError

    def __truediv__(self, other: Any) -> "Value":
        raise NotImplementedError

    # Reflected forms, so `2 - a` and `2 / a` work (module 04b).
    def __radd__(self, other: Any) -> "Value":
        raise NotImplementedError

    def __rmul__(self, other: Any) -> "Value":
        raise NotImplementedError

    def __rsub__(self, other: Any) -> "Value":
        raise NotImplementedError

    def __rtruediv__(self, other: Any) -> "Value":
        raise NotImplementedError

    # -- activations ---------------------------------------------------------------------
    def relu(self) -> "Value":
        raise NotImplementedError

    def tanh(self) -> "Value":
        raise NotImplementedError

    def exp(self) -> "Value":
        raise NotImplementedError

    def log(self) -> "Value":
        """Natural log. Raise ValueError for data <= 0."""
        raise NotImplementedError

    def sigmoid(self) -> "Value":
        raise NotImplementedError

    # -- backprop ------------------------------------------------------------------------
    def backward(self) -> None:
        """Seed this node's gradient with 1.0 and propagate it through the graph.

        Steps:
          1. Build a topological order of all reachable nodes (iterative DFS is safer
             than recursion — deep graphs will blow the recursion limit).
          2. `self.grad = 1.0`
          3. For each node in REVERSE topological order, call `node._backward()`.
        """
        raise NotImplementedError

    def zero_grad(self) -> None:
        """Reset the gradient of every node reachable from here."""
        raise NotImplementedError

    # -- protocol ------------------------------------------------------------------------
    def __repr__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __lt__(self, other: Any) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        return id(self)  # identity, so distinct nodes with equal data stay distinct


def gradcheck(
    func: Callable[..., Value], inputs: list[Value], eps: float = 1e-6, tol: float = 1e-4
) -> bool:
    """Compare analytic gradients against central finite differences.

        (f(x + eps) - f(x - eps)) / (2 * eps)

    Returns True when every input's analytic gradient is within `tol`. Use this on every
    operator you implement — it catches sign errors and missing accumulations instantly.
    """
    raise NotImplementedError

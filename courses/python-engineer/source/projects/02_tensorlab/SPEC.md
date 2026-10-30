# Project 02 — `tensorlab`: build your own PyTorch

Write a reverse-mode automatic differentiation engine and a neural network framework on
top of it. Pure Python + the standard library for milestones 1–5; numpy is allowed (and
sensible) from milestone 6.

This is the best project in the course for *understanding*: by the end, backpropagation
stops being a black box permanently.

**Modules it draws on**: 01 (numerics), 04b (dunder methods — the entire operator surface),
06 (generators, topological iteration), 12 (descriptors and registries for `Module`),
13 (performance).

---

## Milestone 1 — the scalar autograd engine

A `Value` wrapping a single float, recording the graph as you compute.

```python
from tensorlab import Value

a = Value(2.0)
b = Value(-3.0)
c = a * b + a**2        # builds a DAG
c.backward()
a.grad, b.grad          # dc/da = -3 + 2*2 = 1.0 ; dc/db = 2.0
```

Required:
- `Value(data, label="")` with `.data`, `.grad` (starts 0.0), `._prev`, `._op`.
- Operators: `+ - * / ** -` and the reflected forms, so `2 * a` and `1 - a` work.
  Mixing with plain ints/floats is automatic (wrap them).
- `.relu()`, `.tanh()`, `.exp()`, `.log()`, `.sigmoid()`.
- `.backward()` does a **topological sort** of the graph, then applies the chain rule
  in reverse. Gradients **accumulate** (`+=`), which is what makes a node used twice
  (`a*a`) come out right.
- `repr(v)` == `"Value(data=2.0, grad=0.0)"`.
- Comparisons by `.data`, so `sorted(values)` works.

The single most common bug: `=` instead of `+=` on `.grad`. The tests check `a*a`
specifically for that reason.

## Milestone 2 — a tensor

An N-dimensional array with broadcasting, still autograd-aware.

- `Tensor(data, requires_grad=False)` from nested lists; `.shape`, `.ndim`, `.size`, `.dtype`.
- Element-wise `+ - * /` with **broadcasting** (numpy rules), `@` for matmul.
- Reductions: `.sum(axis=None, keepdims=False)`, `.mean()`, `.max()`, `.min()`.
- Shape ops: `.reshape()`, `.transpose()`/`.T`, `.__getitem__` with ints and slices.
- `.backward()` on a scalar-valued tensor, with correct **gradient unbroadcasting**
  (sum over the broadcast axes when propagating back). This is the hard part.
- `.zero_grad()`, `.detach()`, and a `no_grad()` context manager.

## Milestone 3 — the `Module` system

```python
class MLP(Module):
    def __init__(self, sizes: list[int]) -> None:
        super().__init__()
        self.layers = ModuleList([Linear(a, b) for a, b in itertools.pairwise(sizes)])

    def forward(self, x: Tensor) -> Tensor:
        for i, layer in enumerate(self.layers):
            x = layer(x)
            if i < len(self.layers) - 1:
                x = relu(x)
        return x
```

- `Module.__call__` delegates to `.forward` (module 04b).
- `__setattr__` auto-registers `Parameter`s and child `Module`s (module 12) so
  `.parameters()` walks the whole tree recursively.
- `.named_parameters()`, `.zero_grad()`, `.train()`/`.eval()` with a `.training` flag.
- `.state_dict()` / `.load_state_dict()` round-trip through JSON.
- Layers: `Linear` (with Kaiming init), `Sequential`, `ModuleList`, `Dropout`
  (a no-op in eval mode), `LayerNorm`, `Embedding`.

## Milestone 4 — losses and optimisers

- `mse_loss`, `cross_entropy`, `binary_cross_entropy` — numerically stable
  (use log-sum-exp; the tests feed you logits of ±100).
- `Optimizer` base with `.step()` / `.zero_grad()`; implement `SGD` (with momentum,
  weight decay and Nesterov) and `Adam` (with bias correction).
- `lr_scheduler.StepLR` and `CosineAnnealingLR`.

## Milestone 5 — training that actually converges

- `DataLoader(dataset, batch_size, shuffle, seed)` — deterministic under a seed,
  yields batches lazily (module 06).
- A `Trainer` running the loop with callbacks (`on_epoch_end`, early stopping).
- **Acceptance**: train an MLP on XOR to > 99% accuracy in under 2000 epochs, and on a
  synthetic 3-class spiral to > 90%.
- Gradient checking: a `gradcheck(f, inputs, eps=1e-6)` helper comparing analytic
  gradients to central finite differences. Every op you write must pass it.

## Milestone 6 — performance

- Add a numpy backend behind the same API; keep the pure-Python one and pick via
  `tensorlab.set_backend("numpy" | "python")`.
- Benchmark a 3-layer MLP forward+backward at batch 256 on both. Expect ~100×.
- Profile the pure-Python path (module 13) and write down where the time actually went.
- Optional: operator fusion, in-place ops, or a `@jit`-style graph cache.

## Going further

- A transformer block: multi-head attention, positional encoding, and train a character
  language model on a text file.
- `torch.compile`-style graph capture, or a simple kernel-fusion pass.
- CUDA via CuPy behind the same backend switch.
- Export to ONNX, or import PyTorch weights and match its outputs to 1e-5.

## What "done" means

`pytest projects/02_tensorlab` is green, `gradcheck` passes for every op, XOR converges,
and you can explain — out loud, without notes — why gradients must accumulate and what
unbroadcasting is doing.

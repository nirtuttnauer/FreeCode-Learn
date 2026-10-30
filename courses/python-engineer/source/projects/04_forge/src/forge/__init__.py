"""forge — a durable task queue and scheduler.

Design rules that keep a queue honest:
  1. Delivery is AT LEAST ONCE. Tasks must be idempotent. Say it in your README.
  2. Reservation must be atomic, or two workers will run the same job.
  3. Every clock is injected. A scheduler tested against the real clock isn't tested.
  4. Nothing unbounded: queues, retries and in-flight work all have limits.
"""

from __future__ import annotations

__all__ = ["ForgeError", "InvalidTransition", "Job", "JobState", "__version__", "task"]

__version__ = "0.1.0"

from forge.jobs import ForgeError, InvalidTransition, Job, JobState, task

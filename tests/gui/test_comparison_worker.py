"""Tests for `ComparisonWorker`'s signal contract and reusability.

The worker's `start()` method is invoked directly (single-threaded) here
to deterministically verify its started/progress/result/cancelled/failed/
finished signal contract without the added non-determinism of tearing
down a real OS thread inside a test process. The full QThread +
moveToThread wiring (the worker actually running on a persistent
background thread across multiple, repeated comparisons while the GUI
thread stays responsive) is exercised end-to-end by
`test_main_window.py`'s repeated-comparison tests, which drive the real
`MainWindow` -> persistent `QThread` -> `ComparisonWorker` pipeline.
"""
from app.core.models import ComparisonSettings
from app.gui.workers.comparison_worker import ComparisonWorker
from app.services.comparison_service import ComparisonService


def test_worker_emits_result_for_normal_comparison(qapp):
    service = ComparisonService()
    a = service.load_source_from_text("a\nb\nc\n", "A")
    b = service.load_source_from_text("a\nB\nc\n", "B")
    worker = ComparisonWorker(service)

    events = []
    worker.started.connect(lambda: events.append("started"))
    worker.result_ready.connect(lambda r: events.append(("result", r.statistics.modified)))
    worker.failed.connect(lambda info: events.append(("failed", info)))
    worker.cancelled.connect(lambda: events.append("cancelled"))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start(a, b, ComparisonSettings())

    assert events[0] == "started"
    assert ("result", 1) in events
    assert events[-1] == "finished"
    assert not any(e == "cancelled" or (isinstance(e, tuple) and e[0] == "failed") for e in events)


def test_worker_emits_cancelled_when_cancel_requested_during_run(qapp):
    service = ComparisonService()
    big_a = "\n".join(str(i) for i in range(50000))
    big_b = "\n".join(str(i) + "x" for i in range(50000))
    a = service.load_source_from_text(big_a, "A")
    b = service.load_source_from_text(big_b, "B")
    worker = ComparisonWorker(service)

    events = []
    worker.cancelled.connect(lambda: events.append("cancelled"))
    worker.result_ready.connect(lambda r: events.append("result"))
    worker.finished.connect(lambda: events.append("finished"))
    # In real usage, Cancel is only ever clicked while a comparison is
    # already in flight (the button is only enabled then) -- simulate
    # that here by requesting cancellation as soon as the first progress
    # update arrives, which fires well before this large comparison
    # would otherwise complete.
    worker.progress.connect(lambda _pct: worker.request_cancel())

    worker.start(a, b, ComparisonSettings())

    assert "cancelled" in events
    assert "result" not in events
    assert events[-1] == "finished"


def test_worker_emits_failed_on_invalid_input(qapp):
    service = ComparisonService()
    worker = ComparisonWorker(service)

    events = []
    worker.failed.connect(lambda info: events.append(info))
    worker.finished.connect(lambda: events.append("finished"))

    worker.start(None, None, ComparisonSettings())

    assert len(events) == 2
    assert events[0].code == "ETC-INPUT-INVALID"


def test_worker_is_reusable_across_repeated_start_calls(qapp):
    """The whole point of the reusable-worker design: the SAME worker
    instance must be able to run many independent comparisons in
    sequence, each producing its own correct, independent result, with a
    cancel request from one job never leaking into the next."""
    service = ComparisonService()
    worker = ComparisonWorker(service)

    results = []
    worker.result_ready.connect(lambda r: results.append(r.statistics.modified))
    worker.cancelled.connect(lambda: results.append("cancelled"))

    # Job 1: a normal comparison with one modified line.
    a1 = service.load_source_from_text("x\ny\n", "A")
    b1 = service.load_source_from_text("x\nY\n", "B")
    worker.start(a1, b1, ComparisonSettings())

    # Job 2: cancelled (request_cancel during, not before, execution --
    # see the comment in test_worker_emits_cancelled_when_cancel_requested_during_run
    # for why "before start" isn't representative of real GUI usage, and
    # is in fact now impossible by design since start() resets cancel
    # state for each new job).
    a2 = service.load_source_from_text("\n".join(str(i) for i in range(50000)), "A")
    b2 = service.load_source_from_text("\n".join(str(i) + "x" for i in range(50000)), "B")
    cancel_connection = worker.progress.connect(lambda _pct: worker.request_cancel())
    worker.start(a2, b2, ComparisonSettings())
    worker.progress.disconnect(cancel_connection)

    # Job 3: cancellation from job 2 must NOT still be in effect here.
    a3 = service.load_source_from_text("p\nq\n", "A")
    b3 = service.load_source_from_text("p\nQ\n", "B")
    worker.start(a3, b3, ComparisonSettings())

    assert results == [1, "cancelled", 1]

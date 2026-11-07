from app.metrics import Metrics, percentile


def test_percentile_empty_is_zero():
    assert percentile([], 95) == 0.0


def test_percentile_nearest_rank():
    data = list(range(1, 101))
    assert percentile(data, 50) == 50
    assert percentile(data, 95) == 95
    assert percentile([7], 99) == 7


def test_snapshot_counts_and_error_rate():
    m = Metrics()
    m.record_request(10, 200)
    m.record_request(30, 200)
    m.record_request(20, 502)
    snap = m.snapshot()
    assert snap["requests"] == 3
    assert snap["errors"] == 1
    assert snap["error_rate"] == round(1 / 3, 4)
    assert snap["latency_ms"]["max"] == 30
    assert snap["statuses"] == {"200": 2, "502": 1}


def test_ai_test_valid_rate():
    m = Metrics()
    assert m.snapshot()["ai_tests"]["valid_rate"] is None
    m.record_test_check(True)
    m.record_test_check(False)
    assert m.snapshot()["ai_tests"]["valid_rate"] == 0.5


def test_window_limits_latency_history():
    m = Metrics(window=3)
    for i in range(10):
        m.record_request(i, 200)
    assert m.snapshot()["recent_latencies_ms"] == [7, 8, 9]

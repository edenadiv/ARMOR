from cdmas.agents.tma.baseline import RollingBaseline


def test_warmup_suppresses_deviation():
    b = RollingBaseline(warmup=5)
    for _ in range(3):
        b.update(100.0)
    assert b.deviation(100_000.0) == 0.0  # still warming up


def test_deviation_after_warmup():
    b = RollingBaseline(warmup=5)
    for v in [100.0, 102.0, 98.0, 101.0, 99.0, 100.0]:
        b.update(v)
    assert abs(b.mean - 100.0) < 1.0
    assert b.deviation(100.0) < 1.0  # in-band
    assert b.deviation(10_000.0) > 2.0  # spike detected


def test_window_evicts_old_values():
    b = RollingBaseline(window=3, warmup=1)
    for v in [1.0, 2.0, 3.0, 4.0]:
        b.update(v)
    # only last 3 kept ([2,3,4]); the anti-poison baseline reads the oldest-50% of history
    # (excluding the current sample 4) -> hist=[2,3], cutoff=1 -> mean over [2] == 2.0.
    assert abs(b.mean - 2.0) < 1e-9


def test_recent_poison_does_not_shift_baseline():
    # Anti-poisoning: an ongoing attack flooding the most-recent samples must NOT shift the
    # baseline (it reads the oldest 50% of history), so the attack stays out of band.
    b = RollingBaseline(window=60, warmup=5)
    for v in [100.0, 98.0, 102.0, 99.0, 101.0] * 8:  # 40 clean samples ~N(100, ~1.4)
        b.update(v)
    clean_mean, clean_std = b.mean, b.std
    for _ in range(10):  # attack floods recent samples
        b.update(10_000.0)
    assert abs(b.mean - clean_mean) < 5.0  # baseline did not drift toward the attack
    assert b.std < clean_std * 3 + 1.0  # std not blown up by the poison
    assert b.deviation(10_000.0) > 2.0  # ...so the spike is still detected

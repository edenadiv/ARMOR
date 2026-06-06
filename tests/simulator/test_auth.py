from cdmas.common.timing.clock import ManualClock
from cdmas.simulator.auth import RateLimiter, token_ok


def test_token_ok():
    assert token_ok("Bearer secret", "secret") is True
    assert token_ok("Bearer wrong", "secret") is False
    assert token_ok(None, "secret") is False


def test_rate_limiter_allows_burst_then_blocks_then_refills():
    clk = ManualClock()
    rl = RateLimiter(rate_per_s=10, burst=3, clock=clk)
    assert rl.allow("TMA:seg1") is True
    assert rl.allow("TMA:seg1") is True
    assert rl.allow("TMA:seg1") is True
    assert rl.allow("TMA:seg1") is False  # burst exhausted
    clk.advance(1000)  # +1s -> refill (capped at burst)
    assert rl.allow("TMA:seg1") is True


def test_rate_limiter_is_per_key():
    clk = ManualClock()
    rl = RateLimiter(rate_per_s=1, burst=1, clock=clk)
    assert rl.allow("a") is True
    assert rl.allow("a") is False
    assert rl.allow("b") is True  # separate bucket

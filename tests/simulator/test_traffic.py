from cdmas.common.models.enums import Segment
from cdmas.simulator.hosts import HostRegistry
from cdmas.simulator.sampling import classify_kind
from cdmas.simulator.traffic import TrafficGenerator


def test_same_seed_is_deterministic():
    g1 = TrafficGenerator(seed=42)
    g2 = TrafficGenerator(seed=42)
    a = g1.sample(Segment.SERVER, 5)
    b = g2.sample(Segment.SERVER, 5)
    assert [p.freq for p in a] == [p.freq for p in b]
    assert [p.src_ip for p in a] == [p.src_ip for p in b]


def test_rate_tracks_configured_baseline():
    g = TrafficGenerator(seed=1, baselines={Segment.SERVER: (1000.0, 10.0)})
    pkts = g.sample(Segment.SERVER, 300)
    mean_freq = sum(p.freq for p in pkts) / len(pkts)
    assert 950 < mean_freq < 1050


def test_sample_count_and_timestamp():
    g = TrafficGenerator(seed=7)
    pkts = g.sample(Segment.PUBLIC_FACING, 12, ts_ms=500.0)
    assert len(pkts) == 12
    assert all(p.ts_ms == 500.0 for p in pkts)


def test_benign_dst_is_a_named_server():
    g = TrafficGenerator(seed=0)
    targets = {h.ip for h in HostRegistry().targets("server")}
    pkts = g.sample(Segment.SERVER, 50)
    # dst resolves to a named server device; src stays a diverse synthetic client (classifier-safe)
    assert pkts and all(p.dst_ip in targets for p in pkts)


def test_benign_attributes_and_classification_preserved():
    # Gate-safety canary: only IP strings change; count/port/proto/size + benign label hold.
    g = TrafficGenerator(seed=0)
    pkts = g.sample(Segment.PUBLIC_FACING, 50)
    assert len(pkts) == 50
    assert all(p.port == 443 and p.protocol == "TCP" and p.pkt_size == 512 for p in pkts)
    assert all(classify_kind(p) == "benign" for p in pkts)

from cdmas.common.models.enums import Segment
from cdmas.simulator.hosts import HostRegistry


def test_registry_has_named_hosts_per_segment():
    r = HostRegistry()
    for seg in Segment:
        hosts = r.hosts_in(seg.value)
        assert hosts, f"no hosts for {seg.value}"
        assert all(h.segment == seg.value for h in hosts)


def test_get_host_roundtrips_by_ip():
    r = HostRegistry()
    for h in r.all_hosts():
        assert r.get_host(h.ip) is h


def test_target_for_is_a_named_server():
    r = HostRegistry()
    for seg in Segment:
        target_ips = {h.ip for h in r.targets(seg.value)}
        for octet in range(2, 254):
            assert r.target_for(seg.value, octet) in target_ips


def test_primary_target_is_a_named_host():
    r = HostRegistry()
    for seg in Segment:
        ips = {h.ip for h in r.hosts_in(seg.value)}
        assert r.primary_target(seg.value) in ips


def test_to_view_serializes_hosts_for_the_frontend():
    r = HostRegistry()
    view = r.to_view([Segment.SERVER])
    assert view and all(h["segment"] == "server" for h in view)
    assert {"hostname", "ip", "segment", "role", "services"} <= set(view[0].keys())

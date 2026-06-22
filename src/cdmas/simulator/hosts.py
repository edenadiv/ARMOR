"""Named host registry — the device-level network model behind the Packet-Tracer view.

Ported from the prototype's ``HostRegistry``: every segment has named devices (servers,
workstations, IDS) with roles + services, so benign traffic and attacks can flow
device->device by real src/dst IP. The simulator keeps its own Gaussian *volume*; this only
supplies the IP labels (so detection/scoring are unchanged — see ``traffic.py``).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Service(BaseModel):
    port: int
    name: str
    protocol: str = "TCP"


class Host(BaseModel):
    hostname: str
    ip: str
    segment: str  # matches a Segment enum value
    role: str
    os: str = ""
    services: list[Service] = Field(default_factory=list)
    description: str = ""


# Server-tier hostnames that benign traffic flows TO, per segment.
_TARGETS: dict[str, list[str]] = {
    "public-facing": ["web-01", "web-02", "api-01"],
    "server": ["db-primary", "db-replica", "cache-01"],
    "internal": ["dc-01", "fileserver-01"],
    "sec-mon": ["siem-01", "log-collector"],
}


def _hosts() -> list[Host]:
    out: list[Host] = []
    # public-facing
    out += [
        Host(hostname="lb-01", ip="172.16.0.2", segment="public-facing", role="load-balancer",
             os="Linux Ubuntu 22.04", services=[Service(port=443, name="HTTPS")],
             description="HAProxy load balancer — internet entry point"),
        Host(hostname="web-01", ip="172.16.0.10", segment="public-facing", role="web-server",
             os="Linux Ubuntu 22.04", services=[Service(port=443, name="HTTPS")],
             description="Nginx web server (primary)"),
        Host(hostname="web-02", ip="172.16.0.11", segment="public-facing", role="web-server",
             os="Linux Ubuntu 22.04", services=[Service(port=443, name="HTTPS")],
             description="Nginx web server (secondary)"),
        Host(hostname="api-01", ip="172.16.0.20", segment="public-facing", role="api-server",
             os="Linux Ubuntu 22.04", services=[Service(port=8080, name="HTTP-API")],
             description="REST API gateway"),
    ]
    # server zone
    out += [
        Host(hostname="app-01", ip="10.0.2.10", segment="server", role="app-server",
             os="Linux Ubuntu 22.04", services=[Service(port=8080, name="HTTP-APP")],
             description="Application server (primary)"),
        Host(hostname="app-02", ip="10.0.2.11", segment="server", role="app-server",
             os="Linux Ubuntu 22.04", services=[Service(port=8080, name="HTTP-APP")],
             description="Application server (secondary)"),
        Host(hostname="db-primary", ip="10.0.2.20", segment="server", role="database",
             os="Linux Ubuntu 22.04", services=[Service(port=5432, name="PostgreSQL")],
             description="PostgreSQL primary (read-write)"),
        Host(hostname="db-replica", ip="10.0.2.21", segment="server", role="database",
             os="Linux Ubuntu 22.04", services=[Service(port=5432, name="PostgreSQL")],
             description="PostgreSQL replica (read-only)"),
        Host(hostname="cache-01", ip="10.0.2.30", segment="server", role="cache",
             os="Linux Ubuntu 22.04", services=[Service(port=6379, name="Redis")],
             description="Redis in-memory cache"),
    ]
    # internal
    out += [
        Host(hostname="dc-01", ip="10.0.1.2", segment="internal", role="domain-controller",
             os="Windows Server 2022",
             services=[Service(port=389, name="LDAP"), Service(port=445, name="SMB")],
             description="Active Directory domain controller"),
        Host(hostname="fileserver-01", ip="10.0.1.3", segment="internal", role="file-server",
             os="Windows Server 2022", services=[Service(port=445, name="SMB")],
             description="Corporate file server"),
    ]
    for i in range(1, 6):
        out.append(Host(hostname=f"workstation-0{i}", ip=f"10.0.1.{9 + i}", segment="internal",
                        role="workstation", os="Windows 11",
                        services=[Service(port=3389, name="RDP")],
                        description=f"Employee workstation {i}"))
    for i in range(1, 3):
        out.append(Host(hostname=f"laptop-0{i}", ip=f"10.0.1.{19 + i}", segment="internal",
                        role="laptop", os="Windows 11",
                        services=[Service(port=3389, name="RDP")],
                        description=f"Employee laptop {i}"))
    # sec-mon
    out += [
        Host(hostname="siem-01", ip="10.0.3.2", segment="sec-mon", role="siem",
             os="Linux Ubuntu 22.04", services=[Service(port=9200, name="Elasticsearch")],
             description="SIEM — centralised security event correlation"),
        Host(hostname="ids-01", ip="10.0.3.3", segment="sec-mon", role="ids-sensor",
             os="Linux Ubuntu 22.04", services=[Service(port=514, name="Syslog", protocol="UDP")],
             description="Intrusion Detection System sensor"),
        Host(hostname="log-collector", ip="10.0.3.4", segment="sec-mon", role="log-collector",
             os="Linux Ubuntu 22.04", services=[Service(port=514, name="Syslog", protocol="UDP")],
             description="Centralised log and network-flow collector"),
    ]
    return out


class HostRegistry:
    """Single source of truth for named hosts and device-level traffic routing."""

    def __init__(self) -> None:
        self._hosts = _hosts()
        self._by_ip: dict[str, Host] = {h.ip: h for h in self._hosts}

    def all_hosts(self) -> list[Host]:
        return list(self._hosts)

    def hosts_in(self, segment: str) -> list[Host]:
        return [h for h in self._hosts if h.segment == segment]

    def get_host(self, ip: str) -> Host | None:
        return self._by_ip.get(ip)

    def targets(self, segment: str) -> list[Host]:
        names = _TARGETS.get(segment, [])
        servers = [h for h in self.hosts_in(segment) if h.hostname in names]
        return servers or self.hosts_in(segment)

    def primary_target(self, segment: str) -> str:
        """The representative server in a segment (attack dst + benign sink)."""
        t = self.targets(segment)
        return t[0].ip if t else "10.0.0.1"

    def target_for(self, segment: str, octet: int) -> str:
        """A named server in the segment (varied by octet) — the dst for benign + attacks.

        Only the *destination* IP is set from the registry. ``dst_ip`` is never used by the
        feature extractor (which keys off unique *source* IPs + dst *ports*) or the FR checks,
        so swapping it in is byte-identical for detection/classification/scoring.
        """
        targets = self.targets(segment)
        return targets[octet % len(targets)].ip if targets else "10.0.0.1"

    def to_view(self, segments: list[Any]) -> list[dict[str, Any]]:
        """Serialise hosts in the given segments for the frontend (live topology + replay)."""
        wanted = {s.value if hasattr(s, "value") else str(s) for s in segments}
        return [h.model_dump() for h in self._hosts if h.segment in wanted]

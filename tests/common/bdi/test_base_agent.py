from cdmas.common.bdi.base_agent import BaseAgent
from cdmas.common.bdi.belief_base import Belief
from cdmas.common.bdi.goals import Goal
from cdmas.common.bdi.plan import Plan
from cdmas.common.logging.event_log import InMemorySink
from cdmas.common.messaging.acl import ACLMessage
from cdmas.common.messaging.bus import InMemoryBus
from cdmas.common.messaging.topics import Topic
from cdmas.common.models.enums import Performative


class _Echo(BaseAgent):
    """On any alert, set a belief and publish a threat-report."""

    def setup(self) -> None:
        self.subscribe(Topic.ALERTS)
        self.goals.add(Goal(description="respond", priority=1.0))

        async def respond(agent: BaseAgent) -> None:
            await agent.publish(
                ACLMessage(
                    performative=Performative.INFORM,
                    sender=agent.agent_id,
                    receiver="BROADCAST",
                    topic=Topic.THREAT_REPORTS,
                    content={"echoed": agent.beliefs.value("last_alert")},
                )
            )
            agent.beliefs.revise(Belief(predicate="responded", value=True, source=agent.agent_id))

        self.plans.append(
            Plan(
                plan_id="respond",
                trigger=lambda b: (
                    b.value("last_alert") is not None and not b.value("responded", False)
                ),
                precondition=lambda b: True,
                body=respond,
            )
        )

    def on_message(self, message: ACLMessage) -> None:
        self.beliefs.revise(
            Belief(
                predicate="last_alert",
                value=message.content.get("n"),
                source=message.sender,
                lamport_ts=message.lamport_ts,
            )
        )


async def test_agent_id_parsing_and_seq():
    bus = InMemoryBus()
    agent = _Echo(agent_id="ACA:seg1", segment="public-facing", bus=bus)
    assert agent.agent_type == "ACA"


async def test_perceive_reason_act_cycle_and_dedup_seq():
    bus = InMemoryBus()
    producer_sub = bus.subscribe(Topic.THREAT_REPORTS, "OBSERVER")
    agent = _Echo(agent_id="ACA:seg1", segment="public-facing", bus=bus, event_sink=InMemorySink())
    agent.setup()

    # Inject an alert as if from a TMA.
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="TMA:seg1",
            receiver="BROADCAST",
            topic=Topic.ALERTS,
            seq=1,
            content={"n": 7},
        )
    )

    await agent.step()  # perceive -> reason -> act

    out = await producer_sub.get(timeout=1)
    assert out.content["echoed"] == 7
    assert out.seq == 1  # agent's first outbound carries seq 1
    assert agent.beliefs.value("responded") is True

    # Second step with no new input does nothing (plan no longer applicable).
    await agent.step()
    assert await producer_sub.get(timeout=0.05) is None


async def test_outbound_lamport_advances_on_receive():
    bus = InMemoryBus()
    agent = _Echo(agent_id="ACA:seg1", segment="public-facing", bus=bus)
    agent.setup()
    await bus.publish(
        ACLMessage(
            performative=Performative.INFORM,
            sender="TMA:seg1",
            receiver="BROADCAST",
            topic=Topic.ALERTS,
            seq=1,
            content={"n": 1},
        )
    )
    before = agent.clock.time
    await agent.step()
    assert agent.clock.time > before  # clock advanced from receive + send

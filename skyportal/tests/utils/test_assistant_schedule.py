import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

from skyportal.models import AssistantQuery
from skyportal.utils import assistant_schedule
from skyportal.utils.assistant_schedule import grb_evidence, update_schedule


def test_interval_next_check_and_pause():
    now = datetime(2026, 11, 22)
    query = AssistantQuery(interval_minutes=5, active=True)

    update_schedule(query, now)
    assert query.next_run_at == now + timedelta(minutes=5)

    query.active = False
    update_schedule(query, now)
    assert query.next_run_at is None

    query.active = True
    query.interval_minutes = None
    update_schedule(query, now)
    assert query.next_run_at is None


def test_grb_evidence_preserves_upper_limits_and_unknown_duration():
    event = SimpleNamespace(
        aliases=["GRB 261122A"],
        trigger_id="817003945.451964",
        dateobs=datetime(2026, 11, 22, 1, 32, 20),
        circulars={"46329": "Fermi localization", "46330": "MASTER-Net follow-up"},
        gcn_notices=[],
        localizations=[
            SimpleNamespace(id=1, localization_name="271.1_-57.7_3.7", properties=[])
        ],
        properties=[],
        extractions=[
            SimpleNamespace(
                circular_id=46330,
                origin="circex",
                data={"photometry": [{"limiting_mag": 17.8}]},
            )
        ],
    )
    evidence = grb_evidence(event)
    assert evidence["localizations"][0]["cone_radius_arcmin"] == 222
    assert evidence["extractions"][0]["data"]["photometry"] == [{"limiting_mag": 17.8}]
    assert evidence["properties"] == []


def test_grb_evidence_is_queued_only_when_new_or_retryable(monkeypatch):
    now = datetime(2026, 11, 22, 4, 50)
    query = AssistantQuery(id=1, group_id=1, prompt="Review.", dry_run=False)
    event = SimpleNamespace(
        id=1,
        dateobs=datetime(2026, 11, 22, 1, 32, 20),
        circulars={"46329": "Fermi localization"},
    )

    class Session:
        jobs = {}

        async def scalars(self, statement):
            return [event]

        async def scalar(self, statement):
            channel = next(
                value
                for value in statement.compile().params.values()
                if isinstance(value, str) and ":task:grb:" in value
            )
            return self.jobs.get(channel)

    session = Session()
    monkeypatch.setattr(
        assistant_schedule, "grb_evidence", lambda event: event.circulars
    )

    async def targets():
        return [
            target
            async for target in assistant_schedule._grb_targets(
                session, query, now, "Public"
            )
        ]

    original = asyncio.run(targets())
    assert len(original) == 1
    channel = f"query:{query.id}:{original[0][2]}"
    session.jobs[channel] = SimpleNamespace(run_status="completed")
    assert asyncio.run(targets()) == []

    event.circulars["46330"] = "MASTER-Net follow-up"
    updated = asyncio.run(targets())
    assert len(updated) == 1
    assert updated[0][2] != original[0][2]

    channel = f"query:{query.id}:{updated[0][2]}"
    session.jobs[channel] = SimpleNamespace(run_status="queued", modified=now)
    assert asyncio.run(targets()) == []
    session.jobs[channel].run_status = "failed"
    assert asyncio.run(targets()) == updated

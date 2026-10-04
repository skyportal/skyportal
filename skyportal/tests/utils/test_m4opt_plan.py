"""Mapping an M4OPT schedule onto instrument fields.

M4OPT plans on its own sky grid, so the pointings it returns have to be paired
with SkyPortal's fields; these pin that pairing without needing M4OPT or a
solver installed.
"""

from types import SimpleNamespace

import astropy.units as u
import pytest
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from astropy.time import Time

from skyportal.utils import m4opt_plan


def field(pk, ra, dec, field_id=None):
    return SimpleNamespace(id=pk, ra=ra, dec=dec, field_id=field_id or pk)


def schedule(rows, bandpasses=None, field_ids=None):
    """An M4OPT schedule table: (action, ra, dec, seconds) per row."""
    return QTable(
        {
            "action": [row[0] for row in rows],
            "bandpass": bandpasses if bandpasses is not None else [""] * len(rows),
            **({"field_id": field_ids} if field_ids is not None else {}),
            "start_time": Time(
                ["2026-01-01T00:00:00"] * len(rows), format="isot", scale="utc"
            ),
            "duration": [row[3] for row in rows] * u.s,
            "target_coord": SkyCoord(
                [row[1] for row in rows] * u.deg, [row[2] for row in rows] * u.deg
            ),
        }
    )


def test_observations_pair_with_their_nearest_field():
    fields = [field(1, 10.0, 0.0), field(2, 20.0, 0.0)]
    table = schedule([("observe", 20.01, 0.0, 300.0), ("observe", 9.99, 0.0, 120.0)])
    rows = list(m4opt_plan.schedule_rows(table, fields))
    assert [row[0].id for row in rows] == [2, 1]
    assert [row[2] for row in rows] == [300.0, 120.0]


def test_each_observation_keeps_its_own_bandpass():
    """Visits cycle through bandpasses, so the band is per row, not per plan."""
    fields = [field(1, 10.0, 0.0)]
    table = schedule(
        [("observe", 10.0, 0.0, 300.0), ("observe", 10.0, 0.0, 300.0)],
        bandpasses=["ztfg", "ztfr"],
    )
    assert [row[3] for row in m4opt_plan.schedule_rows(table, fields)] == [
        "ztfg",
        "ztfr",
    ]


def test_masked_bandpass_becomes_empty():
    """Non-observation rows mask the column rather than leaving it blank."""
    import numpy as np

    fields = [field(1, 10.0, 0.0)]
    table = schedule([("observe", 10.0, 0.0, 300.0)], bandpasses=["ztfg"])
    table["bandpass"] = np.ma.masked_array(["ztfg"], mask=[True])
    assert [row[3] for row in m4opt_plan.schedule_rows(table, fields)] == [""]


def test_slew_bandpass_is_never_read():
    """Slews carry an empty band and must not become an observation."""
    fields = [field(1, 10.0, 0.0)]
    table = schedule(
        [("observe", 10.0, 0.0, 300.0), ("slew", 10.0, 0.0, 60.0)],
        bandpasses=["ztfg", ""],
    )
    assert [row[3] for row in m4opt_plan.schedule_rows(table, fields)] == ["ztfg"]


def test_slews_are_not_observations():
    """A schedule interleaves slews, which are not exposures."""
    fields = [field(1, 10.0, 0.0)]
    table = schedule([("observe", 10.0, 0.0, 300.0), ("slew", 10.0, 0.0, 60.0)])
    assert len(list(m4opt_plan.schedule_rows(table, fields))) == 1


def test_pointing_with_no_nearby_field_is_dropped():
    """Better to lose an exposure than to attach it to a field elsewhere."""
    fields = [field(1, 10.0, 0.0)]
    table = schedule([("observe", 200.0, 0.0, 300.0)])
    assert list(m4opt_plan.schedule_rows(table, fields, separation=1.0)) == []


def test_separation_is_a_boundary_not_a_suggestion():
    fields = [field(1, 10.0, 0.0)]
    table = schedule([("observe", 10.5, 0.0, 300.0)])
    assert len(list(m4opt_plan.schedule_rows(table, fields, separation=1.0))) == 1
    assert list(m4opt_plan.schedule_rows(table, fields, separation=0.1)) == []


def test_empty_schedule_yields_nothing():
    assert list(m4opt_plan.schedule_rows(schedule([]), [field(1, 10.0, 0.0)])) == []


def _remote_worker(monkeypatch, status, body):
    """A remote M4OPT deployment whose worker answers with `status`."""
    import requests

    class Response:
        status_code = status
        text = body

        def raise_for_status(self):
            error = requests.HTTPError(f"HTTP {status}")
            error.response = self
            raise error

    monkeypatch.setattr(
        m4opt_plan,
        "_config",
        lambda: {"deployment": "remote", "endpoint": "http://worker:8080"},
    )
    monkeypatch.setattr(
        m4opt_plan, "write_skymap", lambda loc, path, when: _write(path)
    )
    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())


def _write(path):
    path.write_bytes(b"not really a skymap")
    return path


def _run(**kw):
    event = Time("2026-01-01T00:00:00")
    return m4opt_plan.run_m4opt(
        object(),
        "ztf",
        start_time=event,
        end_time=event + 1 * u.hour,
        event_time=event,
        **kw,
    )


def test_a_worker_without_the_schedule_route_says_so(monkeypatch):
    """A 404 means the image predates /schedule and serves /solve alone; the
    bare "Not Found" that used to surface named neither."""
    _remote_worker(monkeypatch, 404, '{"detail":"Not Found"}')

    with pytest.raises(m4opt_plan.M4OPTError) as caught:
        _run()
    message = str(caught.value)
    assert "/schedule" in message
    assert "http://worker:8080" in message
    assert "healthz" in message


def test_another_worker_error_is_reported_as_it_comes(monkeypatch):
    _remote_worker(monkeypatch, 502, "M4OPT exited 1: solver missing")

    with pytest.raises(m4opt_plan.M4OPTError) as caught:
        _run()
    assert "solver missing" in str(caught.value)
    assert "/schedule" not in str(caught.value)


def test_mission_lookup_is_configured_per_instrument(monkeypatch):
    monkeypatch.setattr(m4opt_plan, "_config", lambda: {"missions": {"ZTF": "ztf"}})
    assert m4opt_plan.mission_for("ZTF") == "ztf"
    assert m4opt_plan.mission_for("Unmapped") is None


def test_window_ending_before_it_starts_is_rejected(monkeypatch):
    monkeypatch.setattr(m4opt_plan, "_config", dict)
    event = Time("2026-01-01T00:00:00", format="isot", scale="utc")
    with pytest.raises(m4opt_plan.M4OPTError, match="ends before it starts"):
        m4opt_plan.run_m4opt(
            None,
            "ztf",
            start_time=event + 2 * u.hour,
            end_time=event + 1 * u.hour,
            event_time=event,
        )


def test_native_field_ids_join_exactly():
    """A mission with its own grid ids reports the number SkyPortal stores."""
    fields = [field(7, 10.0, 0.0, field_id=1538), field(8, 20.0, 0.0, field_id=42)]
    # Coordinates deliberately useless: the id is what must be used.
    table = schedule(
        [("observe", 0.0, 0.0, 300.0), ("observe", 0.0, 0.0, 120.0)],
        field_ids=[42, 1538],
    )
    assert [row[0].id for row in m4opt_plan.schedule_rows(table, fields)] == [8, 7]


def test_field_id_is_not_the_grid_index():
    """ZTF ids run to 1897 across 1778 fields, so id != index + 1."""
    fields = [field(1, 0.0, 0.0, field_id=1538)]
    table = schedule([("observe", 0.0, 0.0, 300.0)], field_ids=[1419])
    assert list(m4opt_plan.schedule_rows(table, fields)) == []


def test_unknown_field_id_is_dropped():
    fields = [field(1, 10.0, 0.0, field_id=1)]
    table = schedule([("observe", 10.0, 0.0, 300.0)], field_ids=[999])
    assert list(m4opt_plan.schedule_rows(table, fields)) == []


def test_position_matching_still_covers_missions_without_ids():
    """UVEX and ULTRASAT generate their grids, so they report no field_id."""
    fields = [field(1, 10.0, 0.0), field(2, 20.0, 0.0)]
    table = schedule([("observe", 20.01, 0.0, 300.0)])
    assert "field_id" not in table.colnames
    assert [row[0].id for row in m4opt_plan.schedule_rows(table, fields)] == [2]


def test_a_real_m4opt_schedule_parses():
    """A schedule M4OPT actually wrote, not a fixture shaped by hand.

    Hand-built tables agreed with what the mapping expected while the reader
    did not, so the units on `duration` only survived here.
    """
    from pathlib import Path

    path = Path(__file__).parents[1] / "data" / "m4opt_ztf_schedule.ecsv"
    # Through the reader the runner uses, so the reader itself is covered.
    table = m4opt_plan.read_schedule(path)

    observed_ids = {int(row["field_id"]) for row in table[table["action"] == "observe"]}
    fields = [
        SimpleNamespace(id=index, ra=0.0, dec=0.0, field_id=field_id)
        for index, field_id in enumerate(sorted(observed_ids), start=1)
    ]
    rows = list(m4opt_plan.schedule_rows(table, fields))

    assert len(rows) == int((table["action"] == "observe").sum())
    # Durations are seconds, not a dimensionless number that happens to print
    # like one -- the distinction the hand-built fixtures could not catch.
    assert all(isinstance(row[2], float) and row[2] > 0 for row in rows)
    assert {row[3] for row in rows} == {"ztfg", "ztfr"}
    assert all(row[0].field_id in observed_ids for row in rows)


# --- generate_m4opt_plan: the driver that writes the plan --------------------


@pytest.fixture()
def planning(monkeypatch):
    """A request/plan pair wired to a real M4OPT schedule and a stub session.

    The solver is stubbed out -- what is under test is what the driver makes of
    a schedule, not the scheduling.
    """
    from datetime import datetime
    from pathlib import Path
    from unittest import mock

    table = m4opt_plan.read_schedule(
        Path(__file__).parents[1] / "data" / "m4opt_ztf_schedule.ecsv"
    )
    observed = sorted(
        {int(row["field_id"]) for row in table[table["action"] == "observe"]}
    )
    fields = [
        SimpleNamespace(id=100 + n, ra=0.0, dec=0.0, field_id=field_id)
        for n, field_id in enumerate(observed)
    ]

    instrument = SimpleNamespace(
        id=7, name="ZTF", configuration_data={"overhead_per_exposure": 8.0}
    )
    request = SimpleNamespace(
        id=1,
        instrument=instrument,
        localization=SimpleNamespace(table=None),
        gcnevent=SimpleNamespace(dateobs=datetime(2026, 9, 5)),
        payload={
            "start_date": "2026-09-05 00:00:00",
            "end_date": "2026-09-05 06:00:00",
            "filters": "ztfg,ztfr",
            "visits": 2,
            "exposure_time": 300,
        },
        status="pending",
    )
    plan = SimpleNamespace(id=42, status="pending")

    session = mock.MagicMock()
    session.scalars.return_value.unique.return_value.all.return_value = fields

    monkeypatch.setattr(m4opt_plan, "mission_for", lambda name: "ztf")
    monkeypatch.setattr(m4opt_plan, "run_m4opt", lambda *a, **k: table)
    monkeypatch.setattr(m4opt_plan, "publish_plan", mock.MagicMock())
    return SimpleNamespace(
        session=session, plan=plan, request=request, table=table, fields=fields
    )


def _planned(session):
    """The PlannedObservation rows the driver handed to the session."""
    assert session.add_all.call_count == 1
    return session.add_all.call_args[0][0]


def test_driver_writes_one_observation_per_exposure(planning):
    m4opt_plan.generate_m4opt_plan(
        planning.session, [planning.plan], [planning.request]
    )

    expected = int((planning.table["action"] == "observe").sum())
    planned = _planned(planning.session)
    assert len(planned) == expected
    assert planning.plan.status == "complete"


def test_driver_carries_the_bandpass_of_each_visit(planning):
    m4opt_plan.generate_m4opt_plan(
        planning.session, [planning.plan], [planning.request]
    )

    planned = _planned(planning.session)
    # Not "ztfg" on every row: the visits cycle through the requested filters.
    assert {p.filt for p in planned} == {"ztfg", "ztfr"}
    assert all(p.instrument_id == 7 for p in planned)
    assert all(p.overhead_per_exposure == 8.0 for p in planned)
    assert all(p.observation_plan_id == 42 for p in planned)
    assert {p.field_id for p in planned} <= {f.id for f in planning.fields}


def test_an_unmapped_instrument_fails_the_request(planning, monkeypatch):
    monkeypatch.setattr(m4opt_plan, "mission_for", lambda name: None)

    m4opt_plan.generate_m4opt_plan(
        planning.session, [planning.plan], [planning.request]
    )

    assert planning.plan.status == "failed"
    assert "no mission configured" in planning.request.status
    planning.session.rollback.assert_called_once()
    planning.session.add_all.assert_not_called()


def test_an_instrument_with_no_fields_fails_the_request(planning):
    planning.session.scalars.return_value.unique.return_value.all.return_value = []

    m4opt_plan.generate_m4opt_plan(
        planning.session, [planning.plan], [planning.request]
    )

    assert planning.plan.status == "failed"
    assert "no fields" in planning.request.status


def test_a_schedule_with_no_observations_fails_the_request(planning, monkeypatch):
    empty = planning.table[planning.table["action"] == "slew"]
    monkeypatch.setattr(m4opt_plan, "run_m4opt", lambda *a, **k: empty)

    m4opt_plan.generate_m4opt_plan(
        planning.session, [planning.plan], [planning.request]
    )

    assert planning.plan.status == "failed"
    assert "no observations" in planning.request.status


def sized_schedule(observations, slews=0):
    """A schedule holding a given number of exposures, plus optional slews."""
    return QTable({"action": ["observe"] * observations + ["slew"] * slews})


def scheduler_fitting(limit, calls):
    """An M4OPT run that only schedules when asked for `limit` fields or fewer."""

    def attempt(n_fields):
        calls.append(n_fields)
        return sized_schedule(n_fields if n_fields <= limit else 0)

    return attempt


def test_slews_do_not_count_as_observations():
    assert m4opt_plan.observation_count(sized_schedule(0, slews=3)) == 0
    assert m4opt_plan.observation_count(sized_schedule(2, slews=3)) == 2


def test_a_schedule_without_actions_counts_every_row():
    assert m4opt_plan.observation_count(QTable({"field_id": [1, 2]})) == 2


def test_a_feasible_request_is_scheduled_without_searching():
    calls = []
    table = m4opt_plan.largest_feasible_schedule(scheduler_fitting(50, calls), 20)
    assert m4opt_plan.observation_count(table) == 20
    assert calls == [20]


def test_an_over_subscribed_window_falls_back_to_the_most_fields_that_fit():
    calls = []
    table = m4opt_plan.largest_feasible_schedule(scheduler_fitting(12, calls), 20)
    assert m4opt_plan.observation_count(table) == 12
    assert calls[0] == 20
    assert max(calls) == 20


def test_the_search_never_asks_for_more_than_was_requested():
    calls = []
    m4opt_plan.largest_feasible_schedule(scheduler_fitting(3, calls), 50)
    assert max(calls) == 50


def test_a_window_holding_nothing_gives_up():
    calls = []
    assert m4opt_plan.largest_feasible_schedule(scheduler_fitting(0, calls), 20) is None


def test_the_search_is_bounded(monkeypatch):
    """Each step costs a worker round trip, so the search cannot run away."""
    monkeypatch.setattr(m4opt_plan, "MAX_FIELD_SEARCH_STEPS", 3)
    calls = []
    m4opt_plan.largest_feasible_schedule(scheduler_fitting(1, calls), 1000)
    assert len(calls) == 4  # the request itself, then three search steps


def _empty_worker(monkeypatch):
    """A remote worker that answers with a schedule holding no observations."""
    import requests

    class Response:
        status_code = 200
        text = ""

        def raise_for_status(self):
            pass

        def json(self):
            return {"schedule": ""}

    monkeypatch.setattr(
        m4opt_plan,
        "_config",
        lambda: {"deployment": "remote", "endpoint": "http://worker:8080"},
    )
    monkeypatch.setattr(
        m4opt_plan, "write_skymap", lambda loc, path, when: _write(path)
    )
    monkeypatch.setattr(m4opt_plan, "read_schedule", lambda path: sized_schedule(0))
    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())


def test_a_window_that_schedules_nothing_blames_the_field_of_regard(monkeypatch):
    """Distinct from an over-subscribed window, which the search recovers from."""
    _empty_worker(monkeypatch)
    with pytest.raises(m4opt_plan.M4OPTError, match="field of regard"):
        _run(max_fields=4)

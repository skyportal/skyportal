"""Assemble a source's acknowledgment block from what it actually used.

Papers should cite the instance, the broker and filter that found the object,
and every facility and program that supplied its data. All of that is already
recorded per source, so it is derived here rather than left to memory.

Facilities carry their own `acknowledgment` sentence; where one is unset the
facility is named instead, so the block is useful before anyone fills them in.
"""

import sqlalchemy as sa

from baselayer.app.env import load_env

from ..models import (
    Allocation,
    Broker,
    Candidate,
    Filter,
    FollowupRequest,
    Instrument,
    Photometry,
    Spectrum,
    Telescope,
)

_, cfg = load_env()


def _sentence(text):
    """Normalize a fragment so joined sentences read correctly."""
    text = (text or "").strip()
    if text and not text.endswith((".", "!", "?")):
        text += "."
    return text


async def _filters_used(session, user, obj_id):
    """The filters this object passed, and the brokers behind them."""
    rows = (
        await session.execute(
            sa.select(Filter.id, Filter.name, Broker.name)
            .join(Candidate, Candidate.filter_id == Filter.id)
            .outerjoin(Broker, Filter.broker_id == Broker.id)
            .where(Candidate.obj_id == obj_id)
            .distinct()
            .order_by(Filter.name)
        )
    ).all()
    return [
        {"id": filter_id, "filter": name, "broker": broker}
        for filter_id, name, broker in rows
    ]


async def _facilities_used(session, user, obj_id):
    """Instruments that supplied photometry or spectra, with their telescopes."""
    instrument_ids = set(
        (
            await session.scalars(
                sa.select(Photometry.instrument_id).where(Photometry.obj_id == obj_id)
            )
        ).all()
    ) | set(
        (
            await session.scalars(
                sa.select(Spectrum.instrument_id).where(Spectrum.obj_id == obj_id)
            )
        ).all()
    )
    instrument_ids.discard(None)
    if not instrument_ids:
        return []

    rows = (
        await session.execute(
            sa.select(
                Instrument.id,
                Instrument.name,
                Instrument.acknowledgment,
                Telescope.name,
                Telescope.nickname,
                Telescope.acknowledgment,
            )
            .join(Telescope, Instrument.telescope_id == Telescope.id)
            .where(Instrument.id.in_(instrument_ids))
            .order_by(Instrument.name)
        )
    ).all()

    return [
        {
            "id": instrument_id,
            "instrument": instrument,
            "telescope": telescope_nickname or telescope,
            "acknowledgment": instrument_ack or telescope_ack,
        }
        for instrument_id, instrument, instrument_ack, telescope, telescope_nickname, telescope_ack in rows
    ]


async def _programs_used(session, user, obj_id):
    """Allocations this object was observed under."""
    rows = (
        await session.execute(
            sa.select(
                Allocation.id, Allocation.proposal_id, Allocation.pi, Instrument.name
            )
            .join(FollowupRequest, FollowupRequest.allocation_id == Allocation.id)
            .join(Instrument, Allocation.instrument_id == Instrument.id)
            .where(
                FollowupRequest.obj_id == obj_id,
                FollowupRequest.status.notilike("deleted%"),
            )
            .distinct()
        )
    ).all()
    return [
        {
            "id": allocation_id,
            "proposal_id": proposal_id,
            "pi": pi,
            "instrument": instrument,
        }
        for allocation_id, proposal_id, pi, instrument in rows
        if proposal_id or pi
    ]


def assemble_text(site, filters, facilities, programs):
    """Join the parts into the paragraph a paper would paste."""
    parts = []
    if site:
        parts.append(_sentence(site))

    brokers = sorted({f["broker"] for f in filters if f["broker"]})
    filter_names = sorted({f["filter"] for f in filters if f["filter"]})
    if filter_names:
        named = ", ".join(f'"{name}"' for name in filter_names)
        plural = "s" if len(filter_names) > 1 else ""
        clause = f"This object was selected by the {named} filter{plural}"
        if brokers:
            clause += f" on the {', '.join(brokers)} broker"
            clause += "s" if len(brokers) > 1 else ""
        parts.append(_sentence(clause))

    # A facility's own sentence is used verbatim; the rest are named together.
    described = [f["acknowledgment"] for f in facilities if f["acknowledgment"]]
    plain = [
        f"{f['instrument']} on the {f['telescope']}"
        for f in facilities
        if not f["acknowledgment"]
    ]
    parts.extend(_sentence(text) for text in dict.fromkeys(described))
    if plain:
        parts.append(_sentence(f"Data were obtained with {', '.join(plain)}"))

    for program in programs:
        proposal = program["proposal_id"]
        pi = program["pi"]
        clause = "Observations were carried out"
        if proposal:
            clause += f" under proposal {proposal}"
        if pi:
            clause += f" (PI: {pi})"
        parts.append(_sentence(clause))

    return " ".join(part for part in parts if part)


def _excluding(items, ids):
    """Drop the components the caller does not want cited.

    Stated as exclusions, not inclusions: an omitted parameter then means "cite
    everything", and "cite none" is a non-empty list rather than an empty one --
    which query strings cannot carry.
    """
    if not ids:
        return items
    unwanted = set(ids)
    return [item for item in items if item["id"] not in unwanted]


async def build_acknowledgment(
    session,
    user,
    obj_id,
    exclude_filter_ids=None,
    exclude_instrument_ids=None,
    exclude_allocation_ids=None,
):
    """The acknowledgment block for one source, plus the parts it was built from.

    `components` always lists everything detected, so a caller can offer the
    full set to choose from, while `text` reflects the selection. Which filter
    the science actually came from is a human judgement -- an object routinely
    passes many -- so the caller decides and the phrasing stays here.
    """
    filters = await _filters_used(session, user, obj_id)
    facilities = await _facilities_used(session, user, obj_id)
    programs = await _programs_used(session, user, obj_id)
    site = cfg.get("app.acknowledgment") or ""

    return {
        "text": assemble_text(
            site,
            _excluding(filters, exclude_filter_ids),
            _excluding(facilities, exclude_instrument_ids),
            _excluding(programs, exclude_allocation_ids),
        ),
        "components": {
            "site": _sentence(site),
            "filters": filters,
            "facilities": facilities,
            "programs": programs,
        },
    }

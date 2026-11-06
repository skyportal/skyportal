"""Autonomous triage from shared AssistantQuery rows (skybot).

When an analysis completes, any active AssistantQuery whose
``analysis_service_match`` is in the service name and whose group the source is
saved to runs a skybot assistant job of its ``prompt``. The answer is delivered
to the query's subscribers who are members of its group, plus any always-on
``notify_groups`` (a dry-run query runs but notifies no one).

Read-only: it reuses the assistant loop (MCP read tools) and delivers its answer
as a notification and a skybot thread message; nothing is written to the source,
and the classifier's own result stays authoritative. Personal one-off schedules
stay in RecurringAPI; this is the shared, subscribable kind.

Needs a bot user named ``skybot`` (a member of the notify/query groups). Absent
it, triage is skipped.
"""

import math

import sqlalchemy as sa

from baselayer.log import make_log

from ..models import (
    AssistantMessage,
    AssistantQuery,
    AssistantQuerySubscription,
    GroupUser,
    Source,
    User,
)
from .assistant import is_enabled
from .cosmology import establish_cosmology

log = make_log("assistant_triage")

SKYBOT_USERNAME = "skybot"

# Appended to every query run so the answer ends with a machine-readable urgency
# marker; the assistant service posts the comment either way but only notifies
# subscribers when this is "yes".
NOTIFY_SUFFIX = (
    "\n\nFinally, on the very last line output exactly `NOTIFY: yes` if a human "
    "should be alerted promptly (a genuine anomaly, a candidate needing "
    "spectroscopy, or something clearly unusual), otherwise `NOTIFY: no`. Use "
    "`yes` sparingly: most routine classifications are `NOTIFY: no`."
)


def triage_enabled(cfg) -> bool:
    """The master switch: autonomous triage on, and an assistant to run it."""
    settings = (cfg.get("app.assistant") or {}).get("analysis_triage") or {}
    return bool(settings.get("enabled")) and is_enabled(cfg)


def combine_recipients(subscriber_ids, group_member_ids, notify_group_member_ids):
    """Recipients = subscribers who are still in the query's group, plus the
    members of any always-on notify groups."""
    return sorted(
        (set(subscriber_ids) & set(group_member_ids)) | set(notify_group_member_ids)
    )


async def matching_queries(session, analysis):
    """Active AssistantQuery rows this completed analysis triggers: the service
    name contains their match string and the source is saved to their group."""
    name = (getattr(analysis.analysis_service, "name", "") or "").lower()
    if not name:
        return []
    group_ids = set(
        await session.scalars(
            sa.select(Source.group_id).where(
                Source.obj_id == analysis.obj_id, Source.active.is_(True)
            )
        )
    )
    if not group_ids:
        return []
    queries = (
        (
            await session.scalars(
                sa.select(AssistantQuery).where(
                    AssistantQuery.active.is_(True),
                    AssistantQuery.analysis_service_match.isnot(None),
                    AssistantQuery.group_id.in_(group_ids),
                )
            )
        )
        .unique()
        .all()
    )
    return [q for q in queries if q.analysis_service_match.lower() in name]


async def _recipients(session, query):
    subscriber_ids = set(
        await session.scalars(
            sa.select(AssistantQuerySubscription.user_id).where(
                AssistantQuerySubscription.query_id == query.id
            )
        )
    )
    group_member_ids = set(
        await session.scalars(
            sa.select(GroupUser.user_id).where(GroupUser.group_id == query.group_id)
        )
    )
    notify_member_ids = set()
    for gid in query.notify_groups or []:
        notify_member_ids |= set(
            await session.scalars(
                sa.select(GroupUser.user_id).where(GroupUser.group_id == int(gid))
            )
        )
    return combine_recipients(subscriber_ids, group_member_ids, notify_member_ids)


async def enqueue_query_run(session, analysis, query) -> int | None:
    """Create a skybot run for one triggered query; returns the message id (the
    caller posts it to the assistant service), or None if the run is skipped.

    Skipped when skybot is absent, and when it or the query's owner, whose
    access the run reads with, is not a member of the query's group. A
    classification is readable only by the groups the source is saved to, so a
    run outside them reads an empty list and says the analysis does not exist
    -- on the page where everyone else can see it. Saying nothing is the better
    failure.
    """
    skybot = await session.scalar(
        sa.select(User).where(User.username == SKYBOT_USERNAME, User.is_bot.is_(True))
    )
    if skybot is None:
        log(
            f"no bot user named {SKYBOT_USERNAME!r}; skipping query {query.id} "
            f"for {analysis.obj_id}"
        )
        return None
    reads_the_group = await session.scalar(
        sa.select(GroupUser.id).where(
            GroupUser.group_id == query.group_id,
            GroupUser.user_id == skybot.id,
        )
    )
    if reads_the_group is None:
        log(
            f"{SKYBOT_USERNAME!r} is not a member of group {query.group_id}, so it "
            f"cannot read what it would be asked about; skipping query {query.id} "
            f"for {analysis.obj_id}"
        )
        return None
    owner_in_group = await session.scalar(
        sa.select(GroupUser.id).where(
            GroupUser.group_id == query.group_id,
            GroupUser.user_id == query.owner_id,
        )
    )
    if owner_in_group is None:
        log(
            f"the owner of query {query.id} is not a member of group "
            f"{query.group_id}; skipping it for {analysis.obj_id}"
        )
        return None
    notify = None
    if not query.dry_run:
        users = await _recipients(session, query)
        # comment_groups carries where skybot posts the full triage as a bot
        # comment; it runs even with no subscribers, so the group still sees it.
        notify = {"users": users, "comment_groups": [query.group_id]}
    message = AssistantMessage(
        user_id=skybot.id,
        text=query.prompt + NOTIFY_SUFFIX,
        channel=f"query:{query.id}:{analysis.obj_id}",
        context_type=query.context_type or "source",
        context_id=analysis.obj_id,
        notify=notify,
    )
    session.add(message)
    await session.commit()
    return message.id


HOST_CATALOGS = ("LSDR9", "LSDR10", "NED", "DESI_DR1", "AllWISE", "Gaia_DR3", "LSPSC")
CROSSMATCH_RADIUS_ARCSEC = 10.0

FACTS_PROMPT = (
    "You are triaging a transient for astronomers. The facts below were computed "
    "by SkyPortal and are correct. Write the interpretation only, in this format, "
    "in at most five lines:\n"
    "Reading: one or two sentences on what the evidence together suggests and why.\n"
    "Action: one sentence.\n"
    "Caveats: one or two short items.\n"
    "Use only numbers that appear in the facts and never compute new ones. If "
    "something is missing, say it is unknown. Do not restate the facts.\n\n"
    "Facts for {obj_id}:\n{facts}"
)


def flare_result(analysis):
    """The FLARE classification in an analysis read with get_analysis, or None
    when the analysis is not one."""
    results = ((analysis or {}).get("data") or {}).get("results") or {}
    data = results.get("data") if isinstance(results, dict) else None
    if not isinstance(data, dict) or not {"classification", "triage"} <= set(data):
        return None
    return data


def flare_notifies(flare):
    return ((flare.get("triage") or {}).get("priority") or 0) >= 1


def _sep_arcsec(ra1, dec1, ra2, dec2):
    d1, d2 = math.radians(dec1), math.radians(dec2)
    cos = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(
        math.radians(ra1 - ra2)
    )
    return math.degrees(math.acos(min(1.0, max(-1.0, cos)))) * 3600


def _nearest(entries, source):
    found = [
        (_sep_arcsec(source["ra"], source["dec"], e["ra"], e["dec"]), e)
        for e in entries or []
        if e.get("ra") is not None and e.get("dec") is not None
    ]
    return min(found, key=lambda pair: pair[0], default=(None, None))


def _positive(value):
    """Catalogs mark a missing value with -99."""
    return value if value is not None and value > 0 else None


def _classification_facts(flare):
    c = flare.get("classification") or {}
    probabilities = sorted(
        (c.get("probabilities") or {}).items(), key=lambda kv: -kv[1]
    )
    listed = ", ".join(f"{k} {v:.2f}" for k, v in probabilities if v >= 0.01)
    predicted = c.get("predicted")
    if predicted:
        coarse = (c.get("probabilities_coarse") or {}).get(predicted)
        line = f"FLARE class: {predicted}" + (
            f" (probability {coarse:.2f})" if coarse is not None else ""
        )
    else:
        line = "FLARE class: none reported"
    facts = [f"{line}; subclass probabilities: {listed}."]
    coverage = round(100 * (c.get("nominal_coverage") or 0.9))
    facts.append(
        f"{coverage}% conformal prediction set: {{{', '.join(c.get('prediction_set') or [])}}}"
        + (
            "; the most probable subclass is not in it, so the model is unsure."
            if c.get("argmax_excluded_from_set")
            else "."
        )
    )
    if flare.get("n_detections") is not None:
        facts.append(
            f"FLARE used {flare['n_detections']} detections over "
            f"{flare.get('span_days') or 0:.1f} d."
        )
    anomaly = c.get("anomaly") or {}
    if anomaly:
        alarms = anomaly.get("alarms") or {}
        levels = sorted(alarms, key=lambda k: float(k.rstrip("%")))
        raised = [k for k in levels if alarms[k]]
        quiet = [k for k in levels if not alarms[k]]
        if raised:
            alarm = f"anomaly alarm raised at the {raised[0]} false-alarm rate" + (
                f", not at {' or '.join(quiet)}" if quiet else ""
            )
        else:
            alarm = f"no anomaly alarm at any false-alarm rate ({', '.join(levels)})"
        if anomaly.get("energy_percentile") is not None:
            alarm += (
                f"; its anomaly score is at the {anomaly['energy_percentile']:.1f}th "
                "percentile of the stream (a model score, not a physical energy)"
            )
        facts.append(f"Anomaly: {alarm}.")
    triage = flare.get("triage") or {}
    facts.append(
        f"FLARE verdict: {triage.get('verdict')} (priority {triage.get('priority')})."
    )
    return facts


def _light_curve_facts(light_curve):
    facts = []
    for name, band in ((light_curve or {}).get("bands") or {}).items():
        first, peak, last = (
            band["first_detection"],
            band["peak"],
            band["last_detection"],
        )
        line = (
            f"{name}: {band['n_detections']} detections over "
            f"{last['mjd'] - first['mjd']:.1f} d, peak {peak['mag']:.2f} mag"
        )
        if peak["mjd"] - first["mjd"] < 0.5:
            line += " at the first detection"
        else:
            line += (
                f" {peak['mjd'] - first['mjd']:.1f} d after the first detection, "
                f"{first['mag'] - peak['mag']:.2f} mag brighter than it"
            )
        if last["mjd"] - peak["mjd"] < 0.5:
            line += "; the peak is on the latest night, so it may still be rising"
        else:
            line += (
                f"; {last['mag'] - peak['mag']:.2f} mag fainter than peak "
                f"{last['mjd'] - peak['mjd']:.1f} d later"
            )
        limit = band.get("last_upper_limit_before_first_detection")
        if limit:
            line += (
                f"; last non-detection {limit['days_before_first_detection']:.1f} d "
                f"before the first detection (limit {limit['limiting_mag']:.2f} mag)"
            )
        facts.append(line + ".")
    return facts or ["Light curve: unavailable."]


def _host_facts(flare, source, catalogs, peak_mag):
    facts, redshifts = [], []
    if source.get("redshift") is not None:
        origin = source.get("redshift_origin")
        facts.append(
            f"Redshift in SkyPortal: z = {source['redshift']}"
            + (f" ({origin})." if origin else ".")
        )
        redshifts.append((source["redshift"], "the source redshift"))
    context = flare.get("context") or {}
    if context.get("host_sep") is not None:
        facts.append(
            f'Host galaxy matched by FLARE: {context["host_sep"]:.2f}" away'
            + (
                f", r = {context['host_r']:.2f} mag."
                if context.get("host_r") is not None
                else "."
            )
        )
    radius = f'{CROSSMATCH_RADIUS_ARCSEC:.0f}"'
    if catalogs is None:
        facts.append("Catalog cross-match: unavailable.")
    else:
        sep, ned = _nearest(
            [g for g in catalogs.get("NED") or [] if g.get("objtype") == "G"], source
        )
        if ned is not None:
            line = f'NED galaxy {ned.get("_id")}: {sep:.2f}" away'
            if _positive(ned.get("z")) is not None:
                kind = "spectroscopic" if ned.get("z_tech") == "SPEC" else "photometric"
                line += f", {kind} z = {ned['z']:.4f}"
                redshifts.append((ned["z"], f"the NED {kind} redshift"))
            if _positive(ned.get("Diam")) is not None:
                line += f', diameter {ned["Diam"]:.0f}"'
            facts.append(line + ".")
        sep, desi = _nearest(catalogs.get("DESI_DR1"), source)
        if desi is not None and _positive(desi.get("z")) is not None:
            facts.append(
                f'DESI spectrum {sep:.2f}" away: {desi.get("spectype")} at z = {desi["z"]:.4f}.'
            )
            if desi.get("spectype") == "GALAXY":
                redshifts.append((desi["z"], "the DESI host redshift"))
        legacy = (catalogs.get("LSDR10") or []) + (catalogs.get("LSDR9") or [])
        sep, galaxy = _nearest(
            [g for g in legacy if g.get("objtype") not in (None, "PSF", "DUP")], source
        )
        if galaxy is None:
            facts.append(f"Legacy Survey: no galaxy within {radius}.")
        else:
            line = f'Nearest Legacy Survey galaxy: {sep:.2f}" away (type {galaxy["objtype"]}'
            if _positive(galaxy.get("shape_r")) is not None:
                line += f', half-light radius {galaxy["shape_r"]:.1f}"'
            line += ")"
            z_spec, z_phot = (
                _positive(galaxy.get("z_spec")),
                _positive(galaxy.get("z_phot_median")),
            )
            if z_spec is not None:
                line += f", spectroscopic z = {z_spec:.4f}"
                redshifts.append((z_spec, "the host spectroscopic redshift"))
            if z_phot is not None:
                line += f", photometric z = {z_phot:.3f}"
                if _positive(galaxy.get("z_phot_std")) is not None:
                    line += f" ± {galaxy['z_phot_std']:.3f}"
                redshifts.append((z_phot, "the host photometric redshift"))
            facts.append(line + ".")
        sep, wise = _nearest(catalogs.get("AllWISE"), source)
        if wise is None:
            facts.append(f"WISE: no counterpart within {radius}.")
        elif wise.get("w1mpro") is not None and wise.get("w2mpro") is not None:
            color = wise["w1mpro"] - wise["w2mpro"]
            facts.append(
                f'WISE: counterpart {sep:.2f}" away, W1-W2 = {color:.2f} '
                + (
                    "(AGN-like, at least 0.8)."
                    if color >= 0.8
                    else "(not AGN-like, below 0.8)."
                )
            )
        sep, gaia = _nearest(catalogs.get("Gaia_DR3"), source)
        if gaia is None:
            facts.append(f"Gaia DR3: no source within {radius}.")
        else:
            line = f'Gaia DR3: source {sep:.2f}" away'
            if gaia.get("phot_g_mean_mag") is not None:
                line += f", G = {gaia['phot_g_mean_mag']:.2f}"
            if gaia.get("parallax") is not None and gaia.get("parallax_error"):
                snr = gaia["parallax"] / gaia["parallax_error"]
                line += f", parallax at {snr:.1f} sigma" + (
                    " (likely a star)" if snr > 3 else " (not significant)"
                )
            else:
                line += ", no parallax measured"
            facts.append(line + ".")
        sep, psc = _nearest(catalogs.get("LSPSC"), source)
        if psc is not None and psc.get("score") is not None:
            facts.append(
                f"Point-source score of the nearest Legacy Survey object: "
                f"{psc['score']:.3f} (0 is a galaxy, 1 a star)."
            )
    if redshifts and peak_mag is not None:
        redshift, redshift_from = next(
            (r for r in redshifts if "photometric" not in r[1]), redshifts[0]
        )
        distmod = establish_cosmology().distmod(redshift).value
        facts.append(
            f"Peak absolute magnitude from {redshift_from} (z = {redshift:.3f}): "
            f"{peak_mag - distmod:.1f}, without K-correction or extinction."
        )
    elif context.get("M_pseudo") is not None:
        facts.append(f"FLARE pseudo absolute magnitude: {context['M_pseudo']:.1f}.")
    else:
        facts.append("Absolute magnitude: unknown, no redshift.")
    return facts


def _other_classifier_facts(classifications):
    latest = {}
    for c in classifications or []:
        origin = c.get("origin")
        if not c.get("ml") or origin in (None, "FLARE"):
            continue
        if origin not in latest or c["created_at"] > latest[origin]["created_at"]:
            latest[origin] = c
    if not latest:
        return ["Other classifiers: none."]
    return [
        "Other classifiers: "
        + "; ".join(
            f"{origin} {c['classification']} (probability {c.get('probability') or 0:.2f})"
            for origin, c in sorted(latest.items())
        )
        + "."
    ]


def triage_facts(flare, source, light_curve, catalogs, classifications):
    """What a FLARE triage rests on, worked out by the code for the model to interpret."""
    peaks = [
        b["peak"]["mag"] for b in ((light_curve or {}).get("bands") or {}).values()
    ]
    return (
        _classification_facts(flare)
        + _light_curve_facts(light_curve)
        + _host_facts(flare, source or {}, catalogs, min(peaks, default=None))
        + _other_classifier_facts(classifications)
    )

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Observability tools: compute when sources are visible from telescopes."""

import httpx
from astropy.time import Time

from ..server import SKYPORTAL_URL, get_skyportal_token, mcp

# Built-in telescope locations: (lat_deg, lon_deg, elevation_m, timezone_name)
_TELESCOPES = {
    "keck": (19.8263, -155.4747, 4145, "US/Hawaii"),
    "lick": (37.3414, -121.6429, 1283, "US/Pacific"),
    "palomar": (33.3564, -116.8650, 1712, "US/Pacific"),
    "apo": (32.7803, -105.8203, 2788, "US/Mountain"),
    "ctio": (-30.1691, -70.8064, 2207, "America/Santiago"),
    "gemini-n": (19.8238, -155.4690, 4213, "US/Hawaii"),
    "gemini-s": (-30.2407, -70.7367, 2722, "America/Santiago"),
    "vlt": (-24.6275, -70.4044, 2635, "America/Santiago"),
    "subaru": (19.8255, -155.4761, 4163, "US/Hawaii"),
    "ldt": (34.7443, -111.4223, 2360, "US/Arizona"),
    "lco-coj": (-31.2727, 149.0708, 1116, "Australia/Sydney"),
    "lco-elp": (30.6797, -104.0151, 2070, "US/Central"),
    "lco-lsc": (-30.1674, -70.8048, 2198, "America/Santiago"),
    "lco-ogg": (20.7075, -156.2569, 3055, "US/Hawaii"),
    "lco-cpt": (-32.3806, 20.8106, 1460, "Africa/Johannesburg"),
    "lco-tfn": (28.3006, -16.5106, 2390, "Atlantic/Canary"),
}


@mcp.tool()
async def get_source_observability(
    source_id: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    max_airmass: float = 2.0,
    telescopes: str = "Keck,Palomar,Gemini-N,Gemini-S,VLT",
    date: str | None = None,
) -> str:
    """Compute observing windows for a source from specified telescopes.

    USE THIS TOOL for all observability questions. Do NOT use the
    /api/sources/{id}/observability endpoint (that returns a PDF image
    which cannot be parsed).

    Provide either a source_id (auto-resolves RA/Dec from SkyPortal) or
    explicit ra/dec coordinates.

    Args:
        source_id: SkyPortal source ID (e.g., "ZTF20abwysqy"). RA/Dec will
                   be looked up automatically. Requires authentication.
        ra: Right ascension in decimal degrees (J2000). Not needed if
            source_id is provided.
        dec: Declination in decimal degrees (J2000). Not needed if
             source_id is provided.
        max_airmass: Maximum airmass (default 2.0, ~30 deg altitude)
        telescopes: Comma-separated telescope names. Built-in options:
                    Keck, Lick, Palomar, APO, CTIO, Gemini-N, Gemini-S,
                    VLT, Subaru, LDT, LCO-COJ, LCO-ELP, LCO-LSC,
                    LCO-OGG, LCO-CPT, LCO-TFN.
                    Use "all" for all built-in telescopes.
                    Also accepts "fritz" to query all telescopes from your
                    SkyPortal instance (requires authentication).
        date: Date to compute observability for (ISO format, default: tonight).
              e.g., "2024-06-15"

    Returns:
        Per-telescope observing windows with rise/set times (UTC and local),
        transit time, peak altitude, and airmass.
    """
    import math
    from datetime import timezone
    from zoneinfo import ZoneInfo

    import numpy as np
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_sun
    from astropy.time import TimeDelta

    # Resolve RA/Dec from source_id if needed
    if source_id and (ra is None or dec is None):
        token = get_skyportal_token()
        if not token:
            return "Authentication required to look up source coordinates. Provide ra/dec directly or authenticate."
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{SKYPORTAL_URL}/api/sources/{source_id}",
                    headers={"Authorization": f"token {token}"},
                )
            resp.raise_for_status()
            src = resp.json().get("data", {})
            ra = src.get("ra")
            dec = src.get("dec")
            if ra is None or dec is None:
                return f"Could not resolve coordinates for source {source_id}"
        except Exception as e:
            return f"Error looking up source {source_id}: {e}"

    if ra is None or dec is None:
        return "Provide either source_id or both ra and dec."

    target = SkyCoord(ra=ra, dec=dec, unit="deg")

    if date:
        base_time = Time(date)
    else:
        base_time = Time.now()

    # If "fritz" is requested, fetch telescopes from SkyPortal
    if telescopes.strip().lower() == "fritz":
        token = get_skyportal_token()
        if not token:
            return "Authentication required to fetch Fritz telescopes. Use named telescopes instead."
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{SKYPORTAL_URL}/api/telescope",
                    headers={"Authorization": f"token {token}"},
                )
            resp.raise_for_status()
            fritz_telescopes = resp.json().get("data", [])
            tel_list = []
            for t in fritz_telescopes:
                if t.get("fixed_location") and t.get("lat") and t.get("lon"):
                    tel_list.append(
                        {
                            "name": t.get("nickname") or t.get("name"),
                            "lat": t["lat"],
                            "lon": t["lon"],
                            "elevation": t.get("elevation") or 0,
                            "tz": "UTC",
                        }
                    )
        except Exception as e:
            return (
                f"Error fetching Fritz telescopes: {e}. Use named telescopes instead."
            )
    else:
        # Parse telescope list
        if telescopes.strip().lower() == "all":
            tel_names = list(_TELESCOPES.keys())
        else:
            tel_names = [t.strip().lower() for t in telescopes.split(",")]

        tel_list = []
        for name in tel_names:
            if name not in _TELESCOPES:
                available = ", ".join(t.title() for t in sorted(_TELESCOPES))
                return f"Unknown telescope '{name}'. Available: {available}, all, fritz"
            lat, lon, alt, tz = _TELESCOPES[name]
            tel_list.append(
                {
                    "name": name.upper() if name.startswith("lco") else name.title(),
                    "lat": lat,
                    "lon": lon,
                    "elevation": alt,
                    "tz": tz,
                }
            )

    # Compute observability for each telescope
    # Sample every 5 minutes over the next 24 hours
    time_grid = base_time + TimeDelta(np.linspace(0, 24 * 3600, 289), format="sec")

    min_alt_deg = math.degrees(math.asin(1.0 / max_airmass))
    sun_limit_deg = -18  # astronomical twilight

    header = f"Source observability: {source_id + '  ' if source_id else ''}RA={ra:.5f}, Dec={dec:+.5f}"
    lines = [
        header,
        f"Date: {base_time.isot[:10]}  |  Max airmass: {max_airmass}",
        f"{'=' * 72}",
    ]

    for tel in tel_list:
        location = EarthLocation(
            lat=tel["lat"], lon=tel["lon"], height=tel["elevation"]
        )
        altaz_frame = AltAz(obstime=time_grid, location=location)

        # Target altitude over time
        target_altaz = target.transform_to(altaz_frame)
        target_alt = target_altaz.alt.deg  # type: ignore

        # Sun altitude (astronomical twilight: sun below -18 deg)
        sun_altaz = get_sun(time_grid).transform_to(altaz_frame)
        sun_alt = sun_altaz.alt.deg  # type: ignore

        # Observable = target above min_alt AND sun below twilight limit
        observable = (target_alt >= min_alt_deg) & (sun_alt <= sun_limit_deg)  # type: ignore

        # LST at the start
        lst = base_time.sidereal_time("apparent", longitude=tel["lon"])

        try:
            tz = ZoneInfo(tel["tz"])
        except Exception:
            tz = timezone.utc

        lines.append(f"\n{tel['name']}  (lat={tel['lat']:+.2f}, lon={tel['lon']:+.2f})")
        lines.append(f"  LST now: {lst}")

        if not np.any(observable):
            lines.append(
                "  NOT OBSERVABLE tonight (target below airmass limit or daytime)"
            )
            # Still show transit info
            peak_idx = np.argmax(target_alt)  # type: ignore
            peak_alt = target_alt[peak_idx]  # type: ignore
            if peak_alt > 0:  # type: ignore
                transit_utc = time_grid[peak_idx].datetime.replace(tzinfo=timezone.utc)  # type: ignore
                transit_local = transit_utc.astimezone(tz)
                lines.append(
                    f"  Peak alt: {peak_alt:.1f} deg at "
                    f"{transit_utc.strftime('%H:%M')} UTC / "
                    f"{transit_local.strftime('%H:%M')} local"
                )
            else:
                lines.append("  Source never rises above horizon from this site")
            continue

        # Find observable windows
        obs_changes = np.diff(observable.astype(int))
        rise_indices = np.where(obs_changes == 1)[0] + 1
        set_indices = np.where(obs_changes == -1)[0] + 1

        # Handle edge cases: observable at start/end
        if observable[0]:
            rise_indices = np.concatenate([[0], rise_indices])
        if observable[-1]:
            set_indices = np.concatenate([set_indices, [len(observable) - 1]])

        for ri, si in zip(rise_indices, set_indices):
            rise_utc = time_grid[ri].datetime.replace(tzinfo=timezone.utc)  # type: ignore
            set_utc = time_grid[si].datetime.replace(tzinfo=timezone.utc)  # type: ignore
            rise_local = rise_utc.astimezone(tz)
            set_local = set_utc.astimezone(tz)
            duration_hrs = (set_utc - rise_utc).total_seconds() / 3600

            lines.append(
                f"  Observable: {rise_utc.strftime('%H:%M')}–{set_utc.strftime('%H:%M')} UTC"
                f"  ({rise_local.strftime('%H:%M')}–{set_local.strftime('%H:%M')} local)"
                f"  [{duration_hrs:.1f} hrs]"
            )

        # Transit (peak altitude)
        # Only consider nighttime peak
        night_mask = sun_alt <= sun_limit_deg  # type: ignore
        if np.any(night_mask):
            night_alt = np.where(night_mask, target_alt, -90)  # type: ignore
            peak_idx = np.argmax(night_alt)
            peak_alt = night_alt[peak_idx]
            peak_airmass = (
                1.0 / math.sin(math.radians(peak_alt)) if peak_alt > 0 else float("inf")
            )
            transit_utc = time_grid[peak_idx].datetime.replace(tzinfo=timezone.utc)  # type: ignore
            transit_local = transit_utc.astimezone(tz)
            lines.append(
                f"  Transit: {transit_utc.strftime('%H:%M')} UTC / "
                f"{transit_local.strftime('%H:%M')} local  "
                f"(alt={peak_alt:.1f}\u00b0, airmass={peak_airmass:.2f})"
            )

    return "\n".join(lines)

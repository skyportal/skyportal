from skyportal.tests import api

PLOT = "#photometry-plot .js-plotly-plot"
DRAG_LAYER = f"{PLOT} .nsewdrag"

# Total points drawn across every trace, and the x range currently in view.
POINT_COUNT = f"""() => {{
    const el = document.querySelector({PLOT!r});
    return el?.data ? el.data.reduce((n, t) => n + (t.x ? t.x.length : 0), 0) : -1;
}}"""
X_RANGE = f"""() => {{
    const el = document.querySelector({PLOT!r});
    return el?._fullLayout?.xaxis?.range ?? null;
}}"""


# Plotly is imported as a module, so there is no window.Plotly to relayout
# through: the zoom has to come from real mouse events on the drag layer.
def _drag_zoom(page):
    drag = page.locator(DRAG_LAYER).first
    drag.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    box = drag.bounding_box()
    assert box, "photometry plot has no drag layer to zoom on"
    y = box["y"] + box["height"] / 2
    page.mouse.move(box["x"] + box["width"] * 0.35, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.65, y, steps=10)
    page.mouse.up()
    page.wait_for_timeout(1000)


def test_zoom_survives_new_photometry(
    page, super_admin_user, super_admin_token, public_source, public_group, ztf_camera
):
    """Photometry arriving over the websocket leaves the user's zoom alone.

    Refetched points are the same axes with more data on them. Only a change of
    what an axis represents resets the view.
    """
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    page.wait_for_selector(PLOT)
    page.wait_for_timeout(2000)

    before_count = page.evaluate(POINT_COUNT)
    assert before_count > 0, "expected the source to have photometry plotted"

    _drag_zoom(page)
    zoomed = page.evaluate(X_RANGE)
    full = page.evaluate(
        f"""() => {{
        const el = document.querySelector({PLOT!r});
        return el?._fullLayout?.xaxis?._rangeInitial ?? null;
    }}"""
    )
    assert zoomed, "no x range to read after dragging"
    assert zoomed != full, "the drag did not actually zoom the plot"

    # refresh is a query parameter, and defaults to false: without it the
    # server stores the point but pushes nothing, and nothing refetches.
    status, _ = api(
        "POST",
        "photometry",
        data={
            "obj_id": public_source.id,
            "mjd": 59801.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 18.1,
            "magerr": 0.1,
            "limiting_mag": 22.0,
            "magsys": "ab",
        },
        params={"refresh": "true"},
        token=super_admin_token,
    )
    assert status == 200

    # Wait for the point to land in the plot, so a push that never arrives
    # fails here rather than leaving the zoom assertion below to pass vacuously.
    page.wait_for_function(
        f"""() => {{
        const el = document.querySelector({PLOT!r});
        const n = el?.data ? el.data.reduce((a, t) => a + (t.x ? t.x.length : 0), 0) : -1;
        return n > {before_count};
    }}""",
        timeout=30000,
    )

    after = page.evaluate(X_RANGE)
    assert after == zoomed, (
        f"the zoom was reset by new photometry: {zoomed} became {after}"
    )

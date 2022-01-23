import itertools
import math
import json
import collections

import numpy as np
import pandas as pd

from bokeh.core.properties import List, String
from bokeh.layouts import row, column
from bokeh.models import (
    CustomJS,
    HoverTool,
    Range1d,
    Slider,
    Button,
    LinearAxis,
    RadioGroup,
    CategoricalColorMapper,
    Legend,
    LegendItem,
)
from bokeh.models.widgets import (
    CheckboxGroup,
    TextInput,
    NumericInput,
    Panel,
    Tabs,
    Div,
)
from bokeh.plotting import figure, ColumnDataSource

import bokeh.embed as bokeh_embed
from bokeh.transform import factor_mark

from astropy.time import Time

from matplotlib import cm
from matplotlib.colors import rgb2hex

import os
from baselayer.app.env import load_env
from skyportal.models import (
    DBSession,
    Obj,
    Annotation,
    AnnotationOnSpectrum,
    Photometry,
    Instrument,
    Telescope,
    PHOT_ZP,
    Spectrum,
)

import sncosmo

from .enum_types import ALLOWED_SPECTRUM_TYPES

_, cfg = load_env()
# The minimum signal-to-noise ratio to consider a photometry point as detected
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]

SPEC_LINES = {
    'H': ([3970, 4102, 4341, 4861, 6563, 10052, 10941, 12822, 18756], '#ff0000'),
    'He I': ([3889, 4471, 5876, 6678, 7065], '#002157'),
    'He II': ([3203, 4686, 5411, 6560, 6683, 6891, 8237, 10124], '#003b99'),
    'C I': ([8335, 9093, 9406, 9658, 10693, 11330, 11754, 14543], '#8a2be2'),
    'C II': ([3919, 3921, 4267, 5145, 5890, 6578, 7231, 7236, 9234, 9891], '#570199'),
    'C III': ([4647, 4650, 5696, 6742, 8500, 8665, 9711], '#a30198'),
    'C IV': ([4658, 5801, 5812, 7061, 7726, 8859], '#ff0073'),
    'N II': ([3995, 4631, 5005, 5680, 5942, 6482, 6611], '#01fee1'),
    'N III': ([4634, 4641, 4687, 5321, 5327, 6467], '#01fe95'),
    'N IV': ([3479, 3483, 3485, 4058, 6381, 7115], '#00ff4d'),
    'N V': ([4604, 4620, 4945], '#22ff00'),
    'O I': ([6158, 7772, 7774, 7775, 8446, 9263], '#007236'),
    '[O I]': ([5577, 6300, 6363], '#007236'),
    'O II': (
        [3390, 3377, 3713, 3749, 3954, 3973, 4076, 4349, 4416, 4649, 6641, 6721],
        '#00a64d',
    ),
    '[O II]': ([3726, 3729], '#b9d2c5'),
    # The following lines are so-called forbidden O III lines
    # (see https://www.britannica.com/science/forbidden-lines)
    # 'O III': ([4959, 5007], '#00bf59'),
    '[O III]': ([4363, 4959, 5007], '#aeefcc'),
    'O V': ([3145, 4124, 4930, 5598, 6500], '#03d063'),
    'O VI': ([3811, 3834], '#01e46b'),
    'Na I': ([5890, 5896, 8183, 8195], '#aba000'),
    'Mg I': ([3829, 3832, 3838, 4571, 4703, 5167, 5173, 5184, 5528, 8807], '#8c6239'),
    'Mg II': (
        [2796, 2798, 2803, 4481, 7877, 7896, 8214, 8235, 9218, 9244, 9632],
        '#bf874e',
    ),
    'Si I': ([10585, 10827, 12032, 15888], '#6495ed'),
    'Si II': ([4128, 4131, 5958, 5979, 6347, 6371], '#5674b9'),
    'S I': ([9223, 10457, 13809, 18940, 22694], '#ffe4b5'),
    'S II': ([5433, 5454, 5606, 5640, 5647, 6715, 13529, 14501], '#a38409'),
    'Ca I': ([19453, 19753], '#009000'),
    'Ca II': ([3159, 3180, 3706, 3737, 3934, 3969, 8498, 8542, 8662], '#005050'),
    '[Ca II]': ([7292, 7324], '#859797'),
    'Mn I': ([12900, 13310, 13630, 13859, 15184, 15263], '#009090'),
    'Fe I': ([11973], '#cd5c5c'),
    'Fe II': ([4303, 4352, 4515, 4549, 4924, 5018, 5169, 5198, 5235, 5363], '#f26c4f'),
    'Fe III': ([4397, 4421, 4432, 5129, 5158], '#f9917b'),
    'Co II': (
        [15759, 16064, 16361, 17239, 17462, 17772, 21347, 22205, 22497, 23613, 24596],
        '#ffe4e1',
    ),
    'WR WN': (
        [
            4058,
            4341,
            4537,
            4604,
            4641,
            4686,
            4861,
            4945,
            5411,
            5801,
            6563,
            7109,
            7123,
            10124,
        ],
        '#a55031',
    ),
    # H: 4341,4861,6563; HeII: 4686,5411,10124; CIV: 5801;
    # NIII: 4641; NIV: 4058,4537,7109,7123; NV: 4604,4945
    'WR WC/O': (
        [
            3811,
            3834,
            3886,
            4341,
            4472,
            4647,
            4686,
            4861,
            5598,
            5696,
            5801,
            5876,
            6563,
            6678,
            6742,
            7065,
            7236,
            7726,
            9711,
        ],
        '#b9a44f',
    ),
    # H: 4341,4861,6563; HeI: 7065,6678,5876,4472,3886; HeII: 4686;
    # CII: 7236; CIII: 4647,5696,6742,9711; CIV: 5801,7726; OV: 5598; OVI: 3811,3834
    'Galaxy Lines': (
        [
            2025,
            2056,
            2062,
            2066,
            2249,
            2260,
            2343,
            2374,
            2382,
            2576,
            2586,
            2594,
            2599,
            2798,
            2852,
            3727,
            3934,
            3969,
            4341,
            4861,
            4959,
            5007,
            5890,
            5896,
            6548,
            6563,
            6583,
            6717,
            6731,
        ],
        '#8357bd',
    ),
    # H 4341,4861,6563; NII 6548,6583; [OII] 3727; [OIII] 4959,5007;
    # NaI 5890,5896; MgII 2798; SII 6717,6731; CaII H&K 3969,3934
    # ZnII 2025; CrII 2056,2062,2066; FeII 2249,2260,2343,2374,2382,2586,2599;
    # MnII 2576,2594; MgI 2852
    'Tellurics-1': ([6867, 6884], '#e5806b'),
    'Tellurics-2': ([7594, 7621], '#e5806b'),
    'Sky Lines': (
        [
            4168,
            4917,
            4993,
            5199,
            5577,
            5890,
            6236,
            6300,
            6363,
            6831,
            6863,
            6923,
            6949,
            7242,
            7276,
            7316,
            7329,
            7341,
            7359,
            7369,
            7402,
            7437,
            7470,
            7475,
            7480,
            7524,
            7570,
            7713,
            7725,
            7749,
            7758,
            7776,
            7781,
            7793,
            7809,
            7821,
            7840,
            7853,
            7869,
            7879,
            7889,
            7914,
            7931,
            7947,
            7965,
            7978,
            7993,
            8015,
            8026,
            8063,
            8281,
            8286,
            8299,
            8311,
            8346,
            8365,
            8384,
            8399,
            8418,
            8432,
            8455,
            8468,
            8496,
            8507,
            8542,
            8552,
            8632,
            8660,
            8665,
            8768,
            8781,
            8795,
            8831,
            8854,
            8871,
            8889,
            8907,
            8923,
            8947,
            8961,
            8991,
            9004,
            9040,
            9051,
            9093,
            9103,
            9158,
        ],
        '#6dcff6',
    ),
}


class CheckboxWithLegendGroup(CheckboxGroup):
    colors = List(String, help="List of legend colors")

    __implementation__ = ""


tooltip_format = [
    ('mjd', '@mjd{0.000000}'),
    ('flux', '@flux'),
    ('filter', '@filter'),
    ('fluxerr', '@fluxerr'),
    ('mag', '@mag'),
    ('magerr', '@magerr'),
    ('lim_mag', '@lim_mag'),
    ('instrument', '@instrument'),
    ('stacked', '@stacked'),
]
cmap_opt = cm.get_cmap('nipy_spectral')
cmap_uv = cm.get_cmap('cool')
cmap_ir = cm.get_cmap('autumn')

phot_markers = [
    "circle",
    "triangle",
    "square",
    "diamond",
    "inverted_triangle",
    "plus",
    "cross",
    "triangle_pin",
    "square_pin",
]


def get_effective_wavelength(bandpass_name):
    try:
        bandpass = sncosmo.get_bandpass(bandpass_name)
    except ValueError as e:
        raise ValueError(
            f"Could not get bandpass for {bandpass_name} due to sncosmo error: {e}"
        )

    return float(bandpass.wave_eff)


def get_color(wavelength):

    if 0 < wavelength <= 1500:  # EUV
        bandcolor = 'indigo'
    elif 1500 < wavelength <= 2100:  # uvw2
        bandcolor = 'slateblue'
    elif 2100 < wavelength <= 2400:  # uvm2
        bandcolor = 'darkviolet'
    elif 2400 < wavelength <= 3000:  # uvw1
        bandcolor = 'magenta'
    elif 3000 < wavelength <= 4000:  # U, sdss u
        bandcolor = 'blue'
    elif 4000 < wavelength <= 5000:  # B, sdss g
        bandcolor = 'green'
    elif 5000 < wavelength <= 6000:  # V
        bandcolor = 'yellowgreen'
    elif 6000 < wavelength <= 7000:  # sdss r
        bandcolor = 'red'
    elif 7000 < wavelength <= 8000:  # sdss i
        bandcolor = 'orange'
    elif 8000 < wavelength <= 11000:  # sdss z
        bandcolor = 'brown'
    elif 11000 < wavelength < 1e5:  # mm to Radio
        wavelength = np.log10(wavelength)
        cmap = cmap_ir
        cmap_limits = (4, 5)
        rgb = cmap((cmap_limits[1] - wavelength) / (cmap_limits[1] - cmap_limits[0]))[
            :3
        ]
        bandcolor = rgb2hex(rgb)
    else:
        raise ValueError('wavelength out of range for color maps')

    return bandcolor


def annotate_spec(plot, spectra, lower, upper):
    """Annotate photometry plot with spectral markers.

    Parameters
    ----------
    plot : bokeh figure object
        Figure to be annotated.
    spectra : DBSession object
        Results of query for spectra of object.
    lower, upper : float
        Plot limits allowing calculation of annotation symbol y value.
    """
    # get y position of annotation
    text_y = upper - (upper - lower) * 0.05
    s_y = [text_y] * len(spectra)
    s_text = ['S'] * len(spectra)

    # get data from spectra
    s_mjd = [Time(s.observed_at, format='datetime').mjd for s in spectra]
    s_date = [s.observed_at.isoformat() for s in spectra]
    s_tel = [s.instrument.telescope.name for s in spectra]
    s_inst = [s.instrument.name for s in spectra]

    # plot the annotation using data for hover
    if len(s_mjd) > 0:
        spec_r = plot.text(
            x='s_mjd',
            y='s_y',
            text='s_text',
            text_alpha=0.3,
            text_align='center',
            source=ColumnDataSource(
                data=dict(
                    s_mjd=s_mjd,
                    s_y=s_y,
                    s_date=s_date,
                    s_tel=s_tel,
                    s_inst=s_inst,
                    s_text=s_text,
                )
            ),
        )
        plot.add_tools(
            HoverTool(
                tooltips=[
                    ("Spectrum", ""),
                    ("mjd", "@s_mjd{0.000000}"),
                    ("date", "@s_date"),
                    ("tel", "@s_tel"),
                    ("inst", "@s_inst"),
                ],
                renderers=[spec_r],
            )
        )


def add_plot_legend(plot, legend_items, width, legend_orientation, legend_loc):
    """Helper function to add responsive legends to a photometry plot tab"""
    if legend_orientation == "horizontal":
        width_remaining = width - 120
        current_legend_items = []
        for item in legend_items:
            # 0.65 is an estimate of the average aspect ratio of the characters in the Helvetica
            # font (the default Bokeh label font) and 13 is the default label font size.
            # The 30 is the pixel width of the label shape. The 6 is the spacing between label entries
            item_width = len(item.label["value"]) * 0.65 * 13 + 30 + 6
            # We've hit the end of the line, wrap to a new one
            if item_width > width_remaining:
                plot.add_layout(
                    Legend(
                        orientation=legend_orientation,
                        items=current_legend_items,
                        click_policy="hide",
                        location="top_center",
                        margin=3,
                    ),
                    "below",
                )
                width_remaining = width - 120
                current_legend_items = [item]
            else:
                current_legend_items.append(item)
                width_remaining -= item_width
        # Add remaining
        plot.add_layout(
            Legend(
                orientation=legend_orientation,
                items=current_legend_items,
                click_policy="hide",
                location="top_center",
                margin=3,
            ),
            "below",
        )
    else:
        plot.add_layout(
            Legend(
                click_policy="hide",
                items=legend_items,
                location="top_center",
            ),
            legend_loc,
        )


def photometry_plot(obj_id, user, width=600, device="browser"):
    """Create object photometry scatter plot.

    Parameters
    ----------
    obj_id : str
        ID of Obj to be plotted.

    Returns
    -------
    dict
        Returns Bokeh JSON embedding for the desired plot.
    """

    telescope_subquery = Telescope.query_records_accessible_by(user).subquery()
    instrument_subquery = Instrument.query_records_accessible_by(user).subquery()
    data = pd.read_sql(
        Photometry.query_records_accessible_by(user)
        .add_columns(
            telescope_subquery.c.nickname.label("telescope"),
            instrument_subquery.c.name.label("instrument"),
        )
        .join(instrument_subquery, instrument_subquery.c.id == Photometry.instrument_id)
        .join(
            telescope_subquery,
            telescope_subquery.c.id == instrument_subquery.c.telescope_id,
        )
        .filter(Photometry.obj_id == obj_id)
        .statement,
        DBSession().bind,
    )

    if data.empty:
        return None, None, None

    # get spectra to annotate on phot plots
    spectra = (
        Spectrum.query_records_accessible_by(user)
        .filter(Spectrum.obj_id == obj_id)
        .all()
    )

    data['effwave'] = [get_effective_wavelength(f) for f in data['filter']]
    data['color'] = [get_color(w) for w in data['effwave']]

    data.sort_values(by=['effwave'], inplace=True)

    # get marker for each unique instrument
    instruments = list(data.instrument.unique())
    markers = []
    for i, inst in enumerate(instruments):
        markers.append(phot_markers[i % len(phot_markers)])

    filters = list(set(data['filter']))
    ewaves = [get_effective_wavelength(f) for f in filters]
    colors = [get_color(w) for w in ewaves]

    color_mapper = CategoricalColorMapper(factors=filters, palette=colors)
    color_dict = {'field': 'filter', 'transform': color_mapper}

    labels = []
    for i, datarow in data.iterrows():
        label = f'{datarow["instrument"]}/{datarow["filter"]}'
        if datarow['origin'] is not None:
            label += f'/{datarow["origin"]}'
        labels.append(label)

    data['label'] = labels
    data['zp'] = PHOT_ZP
    data['magsys'] = 'ab'
    data['alpha'] = 1.0
    data['lim_mag'] = (
        -2.5 * np.log10(data['fluxerr'] * PHOT_DETECTION_THRESHOLD) + data['zp']
    )

    # Passing a dictionary to a bokeh datasource causes the frontend to die,
    # deleting the dictionary column fixes that
    del data['original_user_data']

    # keep track of things that are only upper limits
    data['hasflux'] = ~data['flux'].isna()

    # calculate the magnitudes - a photometry point is considered "significant"
    # or "detected" (and thus can be represented by a magnitude) if its snr
    # is above PHOT_DETECTION_THRESHOLD
    obsind = data['hasflux'] & (
        data['flux'].fillna(0.0) / data['fluxerr'] >= PHOT_DETECTION_THRESHOLD
    )
    data.loc[~obsind, 'mag'] = None
    data.loc[obsind, 'mag'] = -2.5 * np.log10(data[obsind]['flux']) + PHOT_ZP

    # calculate the magnitude errors using standard error propagation formulae
    # https://en.wikipedia.org/wiki/Propagation_of_uncertainty#Example_formulae
    data.loc[~obsind, 'magerr'] = None
    coeff = 2.5 / np.log(10)
    magerrs = np.abs(coeff * data[obsind]['fluxerr'] / data[obsind]['flux'])
    data.loc[obsind, 'magerr'] = magerrs
    data['obs'] = obsind
    data['stacked'] = False

    split = data.groupby('label', sort=False)

    finite = np.isfinite(data['flux'])
    fdata = data[finite]
    lower = np.min(fdata['flux']) * 0.95
    upper = np.max(fdata['flux']) * 1.05

    xmin = data['mjd'].min() - 2
    xmax = data['mjd'].max() + 2

    # Layout parameters based on device type
    active_drag = None if "mobile" in device or "tablet" in device else "box_zoom"
    tools = (
        'box_zoom,pan,reset'
        if "mobile" in device or "tablet" in device
        else "box_zoom,wheel_zoom,pan,reset,save"
    )
    legend_loc = "below" if "mobile" in device or "tablet" in device else "right"
    legend_orientation = (
        "vertical" if device in ["browser", "mobile_portrait"] else "horizontal"
    )

    # Compute a plot component height based on rough number of legend rows added below the plot
    # Values are based on default sizing of bokeh components and an estimate of how many
    # legend items would fit on the average device screen. Note that the legend items per
    # row is computed more exactly later once labels are extracted from the data (with the
    # add_plot_legend() function).
    #
    # The height is manually computed like this instead of using built in aspect_ratio/sizing options
    # because with the new Interactive Legend approach (instead of the legacy CheckboxLegendGroup), the
    # Legend component is considered part of the plot and plays into the sizing computations. Since the
    # number of items in the legend can alter the needed heights of the plot, using built-in Bokeh options
    # for sizing does not allow for keeping the actual graph part of the plot at a consistent aspect ratio.
    #
    # For the frame width, by default we take the desired plot width minus 64 for the y-axis/label taking
    # up horizontal space

    (
        frame_width,
        aspect_ratio,
        legend_row_height,
        legend_items_per_row,
    ) = get_dimensions_by_device(device, width)

    height = (
        500
        if device == "browser"
        else math.floor(width / aspect_ratio)
        + legend_row_height * int(len(split) / legend_items_per_row)
        + 30  # 30 is the height of the toolbar
    )

    plot = figure(
        frame_width=frame_width,
        height=height,
        active_drag=active_drag,
        tools=tools,
        toolbar_location='above',
        toolbar_sticky=True,
        y_range=(lower, upper),
        min_border_right=16,
        x_axis_location='above',
        sizing_mode="stretch_width",
    )

    plot.xaxis.axis_label = 'MJD'
    now = Time.now().mjd
    plot.extra_x_ranges = {"Days Ago": Range1d(start=now - xmin, end=now - xmax)}
    plot.add_layout(LinearAxis(x_range_name="Days Ago", axis_label="Days Ago"), 'below')

    imhover = HoverTool(tooltips=tooltip_format)
    imhover.renderers = []
    plot.add_tools(imhover)

    model_dict = {}

    legend_items = []
    for i, (label, sdf) in enumerate(split):
        renderers = []

        # for the flux plot, we only show things that have a flux value
        df = sdf[sdf['hasflux']]

        key = f'obs{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='flux',
            color='color',
            marker=factor_mark('instrument', markers, instruments),
            fill_color=color_dict,
            alpha='alpha',
            source=ColumnDataSource(df),
        )
        renderers.append(model_dict[key])
        imhover.renderers.append(model_dict[key])

        key = f'bin{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='flux',
            color='color',
            marker=factor_mark('instrument', markers, instruments),
            fill_color=color_dict,
            source=ColumnDataSource(
                data=dict(
                    mjd=[],
                    flux=[],
                    fluxerr=[],
                    filter=[],
                    color=[],
                    lim_mag=[],
                    mag=[],
                    magerr=[],
                    stacked=[],
                    instrument=[],
                )
            ),
        )
        renderers.append(model_dict[key])
        imhover.renderers.append(model_dict[key])

        key = 'obserr' + str(i)
        y_err_x = []
        y_err_y = []

        for d, ro in df.iterrows():
            px = ro['mjd']
            py = ro['flux']
            err = ro['fluxerr']

            y_err_x.append((px, px))
            y_err_y.append((py - err, py + err))

        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            alpha='alpha',
            source=ColumnDataSource(
                data=dict(
                    xs=y_err_x, ys=y_err_y, color=df['color'], alpha=[1.0] * len(df)
                )
            ),
        )
        renderers.append(model_dict[key])

        key = f'binerr{i}'
        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            # legend_label=label,
            source=ColumnDataSource(data=dict(xs=[], ys=[], color=[])),
        )
        renderers.append(model_dict[key])

        legend_items.append(LegendItem(label=label, renderers=renderers))

    if device == "mobile_portrait":
        plot.xaxis.ticker.desired_num_ticks = 5
    plot.yaxis.axis_label = 'Flux (μJy)'
    plot.toolbar.logo = None

    add_plot_legend(plot, legend_items, width, legend_orientation, legend_loc)
    slider = Slider(
        start=0.0,
        end=15.0,
        value=0.0,
        step=1.0,
        title='Binsize (days)',
        max_width=350,
        margin=(4, 10, 0, 10),
    )

    callback = CustomJS(
        args={'slider': slider, 'n_labels': len(split), **model_dict},
        code=open(
            os.path.join(os.path.dirname(__file__), '../static/js/plotjs', 'stackf.js')
        )
        .read()
        .replace('default_zp', str(PHOT_ZP))
        .replace('detect_thresh', str(PHOT_DETECTION_THRESHOLD)),
    )

    slider.js_on_change('value', callback)

    # Mark the first and last detections
    detection_dates = data[data['hasflux']]['mjd']
    if len(detection_dates) > 0:
        first = round(detection_dates.min(), 6)
        last = round(detection_dates.max(), 6)
        first_color = "#34b4eb"
        last_color = "#8992f5"
        midpoint = (upper + lower) / 2
        line_top = 5 * upper - 4 * midpoint
        line_bottom = 5 * lower - 4 * midpoint
        y = np.linspace(line_bottom, line_top, num=5000)
        first_r = plot.line(
            x=np.full(5000, first),
            y=y,
            line_alpha=0.5,
            line_color=first_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(
                tooltips=[("First detection", f'{first}')],
                renderers=[first_r],
            )
        )
        last_r = plot.line(
            x=np.full(5000, last),
            y=y,
            line_alpha=0.5,
            line_color=last_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(
                tooltips=[("Last detection", f'{last}')],
                renderers=[last_r],
            )
        )

    # Mark when spectra were taken
    annotate_spec(plot, spectra, lower, upper)
    layout = column(slider, plot, width=width, height=height)

    p1 = Panel(child=layout, title='Flux')

    # now make the mag light curve
    ymax = (
        np.nanmax(
            (
                np.nanmax(data.loc[obsind, 'mag']) if any(obsind) else np.nan,
                np.nanmax(data.loc[~obsind, 'lim_mag']) if any(~obsind) else np.nan,
            )
        )
        + 0.1
    )
    ymin = (
        np.nanmin(
            (
                np.nanmin(data.loc[obsind, 'mag']) if any(obsind) else np.nan,
                np.nanmin(data.loc[~obsind, 'lim_mag']) if any(~obsind) else np.nan,
            )
        )
        - 0.1
    )

    plot = figure(
        frame_width=frame_width,
        height=height,
        active_drag=active_drag,
        tools=tools,
        y_range=(ymax, ymin),
        x_range=(xmin, xmax),
        toolbar_location='above',
        toolbar_sticky=True,
        x_axis_location='above',
        sizing_mode="stretch_width",
    )

    plot.xaxis.axis_label = 'MJD'
    now = Time.now().mjd
    plot.extra_x_ranges = {"Days Ago": Range1d(start=now - xmin, end=now - xmax)}
    plot.add_layout(LinearAxis(x_range_name="Days Ago", axis_label="Days Ago"), 'below')

    obj = Obj.get_if_accessible_by(obj_id, user, raise_if_none=True)
    if obj.dm is not None:
        plot.extra_y_ranges = {
            "Absolute Mag": Range1d(start=ymax - obj.dm, end=ymin - obj.dm)
        }
        plot.add_layout(
            LinearAxis(y_range_name="Absolute Mag", axis_label="m - DM"), 'right'
        )

    # Mark the first and last detections again
    detection_dates = data[obsind]['mjd']
    if len(detection_dates) > 0:
        first = round(detection_dates.min(), 6)
        last = round(detection_dates.max(), 6)
        midpoint = (ymax + ymin) / 2
        line_top = 5 * ymax - 4 * midpoint
        line_bottom = 5 * ymin - 4 * midpoint
        y = np.linspace(line_bottom, line_top, num=5000)
        first_r = plot.line(
            x=np.full(5000, first),
            y=y,
            line_alpha=0.5,
            line_color=first_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(
                tooltips=[("First detection", f'{first}')],
                renderers=[first_r],
            )
        )
        last_r = plot.line(
            x=np.full(5000, last),
            y=y,
            line_alpha=0.5,
            line_color=last_color,
            line_width=2,
        )
        plot.add_tools(
            HoverTool(
                tooltips=[("Last detection", f'{last}')],
                renderers=[last_r],
                point_policy='follow_mouse',
            )
        )

    # Mark when spectra were taken
    annotate_spec(plot, spectra, ymax, ymin)

    imhover = HoverTool(tooltips=tooltip_format)
    imhover.renderers = []
    plot.add_tools(imhover)

    model_dict = {}

    # Legend items are individually stored instead of being applied
    # directly when plotting so that they can be separated into multiple
    # Legend() components if needed (to simulate horizontal row wrapping).
    # This is necessary because Bokeh does not support row wrapping with
    # horizontally-oriented legends out-of-the-box.
    legend_items = []
    for i, (label, df) in enumerate(split):
        renderers = []

        unobs_source = df[~df['obs']].copy()
        unobs_source.loc[:, 'alpha'] = 0.8

        key = f'unobs{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='lim_mag',
            color=color_dict,
            marker=factor_mark('instrument', markers, instruments),
            fill_alpha=0.0,
            line_color=color_dict,
            alpha='alpha',
            source=ColumnDataSource(unobs_source),
        )
        renderers.append(model_dict[key])
        imhover.renderers.append(model_dict[key])

        key = f'obs{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='mag',
            color='color',
            marker=factor_mark('instrument', markers, instruments),
            fill_color=color_dict,
            alpha='alpha',
            source=ColumnDataSource(df[df['obs']]),
        )
        renderers.append(model_dict[key])
        imhover.renderers.append(model_dict[key])

        key = f'bin{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='mag',
            color=color_dict,
            marker=factor_mark('instrument', markers, instruments),
            fill_color='color',
            source=ColumnDataSource(
                data=dict(
                    mjd=[],
                    flux=[],
                    fluxerr=[],
                    filter=[],
                    color=[],
                    lim_mag=[],
                    mag=[],
                    magerr=[],
                    instrument=[],
                    stacked=[],
                )
            ),
        )
        renderers.append(model_dict[key])
        imhover.renderers.append(model_dict[key])

        key = 'obserr' + str(i)
        y_err_x = []
        y_err_y = []

        for d, ro in df[df['obs']].iterrows():
            px = ro['mjd']
            py = ro['mag']
            err = ro['magerr']

            y_err_x.append((px, px))
            y_err_y.append((py - err, py + err))

        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            alpha='alpha',
            source=ColumnDataSource(
                data=dict(
                    xs=y_err_x,
                    ys=y_err_y,
                    color=df[df['obs']]['color'],
                    alpha=[1.0] * len(df[df['obs']]),
                )
            ),
        )
        renderers.append(model_dict[key])

        key = f'binerr{i}'
        model_dict[key] = plot.multi_line(
            xs='xs',
            ys='ys',
            color='color',
            source=ColumnDataSource(data=dict(xs=[], ys=[], color=[])),
        )
        renderers.append(model_dict[key])

        key = f'unobsbin{i}'
        model_dict[key] = plot.scatter(
            x='mjd',
            y='lim_mag',
            color='color',
            marker='inverted_triangle',
            fill_color='white',
            line_color=color_dict,
            alpha=0.8,
            source=ColumnDataSource(
                data=dict(
                    mjd=[],
                    flux=[],
                    fluxerr=[],
                    filter=[],
                    color=[],
                    lim_mag=[],
                    mag=[],
                    magerr=[],
                    instrument=[],
                    stacked=[],
                )
            ),
        )
        imhover.renderers.append(model_dict[key])
        renderers.append(model_dict[key])

        key = f'all{i}'
        model_dict[key] = ColumnDataSource(df)

        key = f'bold{i}'
        model_dict[key] = ColumnDataSource(
            df[
                [
                    'mjd',
                    'flux',
                    'fluxerr',
                    'mag',
                    'magerr',
                    'filter',
                    'zp',
                    'magsys',
                    'lim_mag',
                    'stacked',
                ]
            ]
        )

        legend_items.append(LegendItem(label=label, renderers=renderers))

    add_plot_legend(plot, legend_items, width, legend_orientation, legend_loc)

    plot.yaxis.axis_label = 'AB mag'
    plot.toolbar.logo = None

    slider = Slider(
        start=0.0,
        end=15.0,
        value=0.0,
        step=1.0,
        title='Binsize (days)',
        max_width=350,
        margin=(4, 10, 0, 10),
    )

    button = Button(label="Export Bold Light Curve to CSV")
    button.js_on_click(
        CustomJS(
            args={'slider': slider, 'n_labels': len(split), **model_dict},
            code=open(
                os.path.join(
                    os.path.dirname(__file__), '../static/js/plotjs', "download.js"
                )
            )
            .read()
            .replace('objname', obj_id)
            .replace('default_zp', str(PHOT_ZP)),
        )
    )

    # Don't need to expose CSV download on mobile
    top_layout = (
        slider if "mobile" in device or "tablet" in device else row(slider, button)
    )

    callback = CustomJS(
        args={'slider': slider, 'n_labels': len(split), **model_dict},
        code=open(
            os.path.join(os.path.dirname(__file__), '../static/js/plotjs', 'stackm.js')
        )
        .read()
        .replace('default_zp', str(PHOT_ZP))
        .replace('detect_thresh', str(PHOT_DETECTION_THRESHOLD)),
    )
    slider.js_on_change('value', callback)
    layout = column(top_layout, plot, width=width, height=height)

    p2 = Panel(child=layout, title='Mag')

    # now make period plot

    # get periods from annotations
    annotation_list = (
        Annotation.query_records_accessible_by(user)
        .filter(Annotation.obj_id == obj.id)
        .all()
    )
    period_labels = []
    period_list = []
    for an in annotation_list:
        if 'period' in an.data:
            period_list.append(an.data['period'])
            period_labels.append(an.origin + ": %.9f" % an.data['period'])

    if len(period_list) > 0:
        period = period_list[0]
    else:
        period = None
    # don't generate if no period annotated
    if period is not None:
        # bokeh figure for period plotting
        period_plot = figure(
            frame_width=frame_width,
            height=height,
            active_drag=active_drag,
            tools=tools,
            y_range=(ymax, ymin),
            x_range=(-0.01, 2.01),  # initially one phase
            toolbar_location='above',
            toolbar_sticky=False,
            x_axis_location='below',
            sizing_mode="stretch_width",
        )

        # axis labels
        period_plot.xaxis.axis_label = 'phase'
        period_plot.yaxis.axis_label = 'mag'
        period_plot.toolbar.logo = None

        # do we have a distance modulus (dm)?
        obj = Obj.get_if_accessible_by(obj_id, user)
        if obj.dm is not None:
            period_plot.extra_y_ranges = {
                "Absolute Mag": Range1d(start=ymax - obj.dm, end=ymin - obj.dm)
            }
            period_plot.add_layout(
                LinearAxis(y_range_name="Absolute Mag", axis_label="m - DM"), 'right'
            )

        # initiate hover tool
        period_imhover = HoverTool(tooltips=tooltip_format)
        period_imhover.renderers = []
        period_plot.add_tools(period_imhover)

        # initiate period radio buttons
        period_selection = RadioGroup(labels=period_labels, active=0)

        phase_selection = RadioGroup(labels=["One phase", "Two phases"], active=1)

        # store all the plot data
        period_model_dict = {}

        # iterate over each filter
        legend_items = []
        for i, (label, df) in enumerate(split):
            renderers = []
            # fold x-axis on period in days
            df['mjd_folda'] = (df['mjd'] % period) / period
            df['mjd_foldb'] = df['mjd_folda'] + 1.0

            # phase plotting
            for ph in ['a', 'b']:
                key = 'fold' + ph + f'{i}'
                period_model_dict[key] = period_plot.scatter(
                    x='mjd_fold' + ph,
                    y='mag',
                    color='color',
                    marker=factor_mark('instrument', markers, instruments),
                    fill_color=color_dict,
                    alpha='alpha',
                    # visible=('a' in ph),
                    source=ColumnDataSource(df[df['obs']]),  # only visible data
                )
                # add to hover tool
                period_imhover.renderers.append(period_model_dict[key])
                renderers.append(period_model_dict[key])

                # errorbars for phases
                key = 'fold' + ph + f'err{i}'
                y_err_x = []
                y_err_y = []

                # get each visible error value
                for d, ro in df[df['obs']].iterrows():
                    px = ro['mjd_fold' + ph]
                    py = ro['mag']
                    err = ro['magerr']
                    # set up error tuples
                    y_err_x.append((px, px))
                    y_err_y.append((py - err, py + err))
                # plot phase errors
                period_model_dict[key] = period_plot.multi_line(
                    xs='xs',
                    ys='ys',
                    color='color',
                    alpha='alpha',
                    # visible=('a' in ph),
                    source=ColumnDataSource(
                        data=dict(
                            xs=y_err_x,
                            ys=y_err_y,
                            color=df[df['obs']]['color'],
                            alpha=[1.0] * len(df[df['obs']]),
                        )
                    ),
                )
                renderers.append(period_model_dict[key])

            legend_items.append(LegendItem(label=label, renderers=renderers))

        add_plot_legend(
            period_plot, legend_items, width, legend_orientation, legend_loc
        )

        # set up period adjustment text box
        period_title = Div(text="Period (days): ")
        period_textinput = TextInput(value=str(period if period is not None else 0.0))
        period_textinput.js_on_change(
            'value',
            CustomJS(
                args={
                    'textinput': period_textinput,
                    'numphases': phase_selection,
                    'n_labels': len(split),
                    'p': period_plot,
                    **period_model_dict,
                },
                code=open(
                    os.path.join(
                        os.path.dirname(__file__), '../static/js/plotjs', 'foldphase.js'
                    )
                ).read(),
            ),
        )
        # a way to modify the period
        period_double_button = Button(label="*2", width=30)
        period_double_button.js_on_click(
            CustomJS(
                args={'textinput': period_textinput},
                code="""
                const period = parseFloat(textinput.value);
                textinput.value = parseFloat(2.*period).toFixed(9);
                """,
            )
        )
        period_halve_button = Button(label="/2", width=30)
        period_halve_button.js_on_click(
            CustomJS(
                args={'textinput': period_textinput},
                code="""
                        const period = parseFloat(textinput.value);
                        textinput.value = parseFloat(period/2.).toFixed(9);
                        """,
            )
        )
        # a way to select the period
        period_selection.js_on_click(
            CustomJS(
                args={'textinput': period_textinput, 'periods': period_list},
                code="""
                textinput.value = parseFloat(periods[this.active]).toFixed(9);
                """,
            )
        )
        phase_selection.js_on_click(
            CustomJS(
                args={
                    'textinput': period_textinput,
                    'numphases': phase_selection,
                    'n_labels': len(split),
                    'p': period_plot,
                    **period_model_dict,
                },
                code=open(
                    os.path.join(
                        os.path.dirname(__file__), '../static/js/plotjs', 'foldphase.js'
                    )
                ).read(),
            )
        )

        # layout
        if device == "mobile_portrait":
            period_controls = column(
                row(
                    period_title,
                    period_textinput,
                    period_double_button,
                    period_halve_button,
                    width=width,
                    sizing_mode="scale_width",
                ),
                phase_selection,
                period_selection,
                width=width,
            )
            # Add extra height to plot based on period control components added
            # 18 is the height of each period selection radio option (per default font size)
            # and the 130 encompasses the other components which are consistent no matter
            # the data size.
            height += 130 + 18 * len(period_labels)
        else:
            period_controls = column(
                row(
                    period_title,
                    period_textinput,
                    period_double_button,
                    period_halve_button,
                    phase_selection,
                    width=width,
                    sizing_mode="scale_width",
                ),
                period_selection,
                margin=10,
            )
            # Add extra height to plot based on period control components added
            # Numbers are derived in similar manner to the "mobile_portrait" case above
            height += 90 + 18 * len(period_labels)

        period_layout = column(period_plot, period_controls, width=width, height=height)

        # Period panel
        p3 = Panel(child=period_layout, title='Period')

        # tabs for mag, flux, period
        tabs = Tabs(tabs=[p2, p1, p3], width=width, height=height, sizing_mode='fixed')
    else:
        # tabs for mag, flux
        tabs = Tabs(tabs=[p2, p1], width=width, height=height + 90, sizing_mode='fixed')
    return bokeh_embed.json_item(tabs)


def spectroscopy_plot(
    obj_id,
    user,
    spec_id=None,
    width=600,
    device="browser",
    smoothing=False,
    smooth_number=10,
):
    """
    Create object spectroscopy line plot.

    Parameters
    ----------
    obj_id : str
        ID of Obj to be plotted.
    user :
        The user object that is requesting the plot.
    spec_id : str or None
        A string with a single spectrum ID or a
        comma-separated list of IDs.
        Only the spectra with matching IDs
        are plotted.
        If None (default), will plot all
        spectra associated with the object
        and accessible to the user.
    width : int
        Size of the plot in pixels. Default=600.
    device : str
        Choose one of the following options to describe
        the device on which the plot will be displayed:
        - "browser" (default)
        - "mobile_portrait"
        - "mobile_landscape"
        - "tablet_portrait"
        - "tablet_landscape"
    smoothing: bool
        choose if to start the display with the smoothed plot or the full resolution spectrum.
        default is no smoothing.
    smooth_number: int
        number of data points to use in the moving average when displaying the smoothed spectrum.
        default is 10 points.

    Returns
    -------
    dict
        Bokeh JSON embedding of the plot.

    """

    obj = Obj.get_if_accessible_by(obj_id, user)
    spectra = (
        Spectrum.query_records_accessible_by(user)
        .filter(Spectrum.obj_id == obj_id)
        .all()
    )

    # Accept a string with a single spectrum ID
    # or a comma separated list of IDs.
    # If no IDs are given, choose all Object's spectra.
    if spec_id is not None and len(spec_id) > 0:
        spec_id = spec_id.split(',')
        filtered_spectra = []
        # choose any of the object's spectra that match one of the IDs given
        for sid in spec_id:
            filtered_spectra.extend([spec for spec in spectra if spec.id == int(sid)])
        spectra = filtered_spectra
    if len(spectra) == 0:
        return None, None, None

    # sort out the size of the plot

    spectra_by_type = collections.defaultdict(list)

    for s in spectra:
        spectra_by_type[s.type].append(s)

    # sort the dictionary to be ordered according to the given list
    def sorted_dict(d, key_list):
        return {key: d[key] for key in key_list if key in d}

    # we want the tabs to appear in the order they're defined in the config:
    spectra_by_type = sorted_dict(spectra_by_type, ALLOWED_SPECTRUM_TYPES)

    layouts = []
    for spec_type in spectra_by_type:
        layouts.append(
            make_spectrum_layout(
                obj,
                spectra_by_type[spec_type],
                user,
                device,
                width,
                smoothing,
                smooth_number,
            )
        )

    if len(layouts) > 1:
        panels = []
        spectrum_types = [s for s in spectra_by_type]
        for i, layout in enumerate(layouts):
            panels.append(Panel(child=layout, title=spectrum_types[i]))
        tabs = Tabs(
            tabs=panels, width=width, height=layouts[0].height + 60, sizing_mode='fixed'
        )
        return bokeh_embed.json_item(tabs)

    return bokeh_embed.json_item(layouts[0])


def make_spectrum_layout(obj, spectra, user, device, width, smoothing, smooth_number):
    """
    Helper function that takes the object, spectra and user info,
    as well as the total width of the figure,
    and produces one layout for a spectrum plot.
    This can be used once for each tab on the spectrum plot,
    if using different spectrum types.

    Parameters
    ----------
    obj : dict
        The underlying object that is associated with all these spectra.
    spectra : dict
        The different spectra to be plotted. This can be a subset of
        e.g., all the spectra of one type.
    user : dict
        info about the user, used to get the individual user plot preferences.
    device: string
        name of the device used ("browser", "mobile", "mobile_portrait", "tablet", etc).
    width: int
        width of the external frame of the plot, including the buttons/sliders.
    smoothing: bool
        choose if to start the display with the smoothed plot or the full resolution spectrum.
    smooth_number: int
        number of data points to use in the moving average when displaying the smoothed spectrum.

    Returns
    -------
    dict
        Bokeh JSON embedding of one layout that can be tabbed or
        used as the plot specifications on its own.
    """
    rainbow = cm.get_cmap('rainbow', len(spectra))
    palette = list(map(rgb2hex, rainbow(range(len(spectra)))))
    color_map = dict(zip([s.id for s in spectra], palette))

    data = []
    for i, s in enumerate(spectra):
        # normalize spectra to a median flux of 1 for easy comparison
        normfac = np.nanmedian(np.abs(s.fluxes))
        normfac = normfac if normfac != 0.0 else 1e-20
        altdata = json.dumps(s.altdata) if s.altdata is not None else ""
        annotations = (
            AnnotationOnSpectrum.query_records_accessible_by(user)
            .filter(AnnotationOnSpectrum.spectrum_id == s.id)
            .all()
        )
        annotations = (
            json.dumps([{a.origin: a.data} for a in annotations])
            if len(annotations)
            else ""
        )

        df = pd.DataFrame(
            {
                'wavelength': s.wavelengths,
                'flux': s.fluxes / normfac,
                'flux_original': s.fluxes / normfac,
                'id': s.id,
                'telescope': s.instrument.telescope.name,
                'instrument': s.instrument.name,
                'date_observed': s.observed_at.isoformat(sep=' ', timespec='seconds'),
                'pi': (
                    s.assignment.run.pi
                    if s.assignment is not None
                    else (
                        s.followup_request.allocation.pi
                        if s.followup_request is not None
                        else ""
                    )
                ),
                'origin': s.origin,
                'altdata': altdata[:20] + "..." if len(altdata) > 20 else altdata,
                'annotations': annotations,
            }
        )
        data.append(df)

    data = pd.concat(data)
    data.sort_values(by=['date_observed', 'wavelength'], inplace=True)

    split = data.groupby('id', sort=False)

    (
        frame_width,
        aspect_ratio,
        legend_row_height,
        legend_items_per_row,
    ) = get_dimensions_by_device(device, width)

    plot_height = (
        math.floor(width / aspect_ratio)
        if device == "browser"
        else math.floor(width / aspect_ratio)
        + legend_row_height * int(len(split) / legend_items_per_row)
        + 30  # 30 is the height of the toolbar
    )

    # Add some height for the checkboxes and sliders
    if device == "mobile_portrait":
        height = plot_height + 440
    elif device == "mobile_landscape":
        height = plot_height + 370
    else:
        height = plot_height + 220

    # check browser plot_height for legend overflow
    if device == "browser":
        plot_height_of_legend = (
            legend_row_height * int(len(split) / legend_items_per_row)
            + 90  # 90 is height of toolbar plus legend offset
        )

        if plot_height_of_legend > plot_height:
            plot_height = plot_height_of_legend

    hover = HoverTool(
        tooltips=[
            ('wavelength', '@wavelength{0,0.000}'),
            ('flux', '@flux'),
            ('telesecope', '@telescope'),
            ('instrument', '@instrument'),
            ('UTC date observed', '@date_observed'),
            ('PI', '@pi'),
            ('origin', '@origin'),
            ('altdata', '@altdata{safe}'),
            ('annotations', '@annotations{safe}'),
        ],
    )

    flux_max = np.max(data['flux'])
    flux_min = np.min(data['flux'])
    ymax = flux_max * 1.05
    ymin = flux_min - 0.05 * (flux_max - flux_min)
    xmin = np.min(data['wavelength']) - 100
    xmax = np.max(data['wavelength']) + 100
    if obj.redshift is not None and obj.redshift > 0:
        xmin_rest = xmin / (1.0 + obj.redshift)
        xmax_rest = xmax / (1.0 + obj.redshift)

    active_drag = None if "mobile" in device or "tablet" in device else "box_zoom"
    tools = (
        "box_zoom, pan, reset"
        if "mobile" in device or "tablet" in device
        else "box_zoom,wheel_zoom,pan,reset"
    )

    plot = figure(
        frame_width=frame_width,
        height=plot_height,
        y_range=(ymin, ymax),
        x_range=(xmin, xmax),
        tools=tools,
        toolbar_location="above",
        active_drag=active_drag,
    )

    model_dict = {}
    legend_items = []
    for i, (key, df) in enumerate(split):

        renderers = []
        s = next(spec for spec in spectra if spec.id == key)
        if s.label is not None and len(s.label) > 0:
            label = s.label
        else:
            label = f'{s.instrument.name} ({s.observed_at.date().strftime("%m/%d/%y")})'
        model_dict['s' + str(i)] = plot.step(
            x='wavelength',
            y='flux',
            color=color_map[key],
            source=ColumnDataSource(df),
        )
        renderers.append(model_dict[f's{i}'])

        # this starts out the same as the previous plot, but can be binned/smoothed later in JS
        model_dict[f'bin{i}'] = plot.step(
            x='wavelength', y='flux', color=color_map[key], source=ColumnDataSource(df)
        )
        renderers.append(model_dict[f'bin{i}'])

        # add this line plot to be able to show tooltip at hover
        model_dict['l' + str(i)] = plot.line(
            x='wavelength',
            y='flux',
            color=color_map[key],
            source=ColumnDataSource(df),
            line_alpha=0.0,
        )
        renderers.append(model_dict[f'l{i}'])

        legend_items.append(LegendItem(label=label, renderers=renderers))

    plot.xaxis.axis_label = 'Wavelength (Å)'
    plot.yaxis.axis_label = 'Flux'
    plot.toolbar.logo = None
    if obj.redshift is not None and obj.redshift > 0:
        plot.extra_x_ranges = {"rest_wave": Range1d(start=xmin_rest, end=xmax_rest)}
        plot.add_layout(
            LinearAxis(x_range_name="rest_wave", axis_label="Rest Wavelength (Å)"),
            'above',
        )

    # TODO how to choose a good default?
    plot.y_range = Range1d(0, 1.03 * data.flux.max())

    legend_loc = "below" if "mobile" in device or "tablet" in device else "right"
    legend_orientation = (
        "vertical" if device in ["browser", "mobile_portrait"] else "horizontal"
    )

    add_plot_legend(plot, legend_items, width, legend_orientation, legend_loc)
    # only show this tooltip for spectra, not elemental lines
    hover.renderers = list(model_dict.values())
    plot.add_tools(hover)

    smooth_checkbox = CheckboxGroup(
        labels=["smoothing"],
        active=[0] if smoothing else [],
    )
    smooth_slider = Slider(
        start=0.0,
        end=100.0,
        value=0.0,
        step=1.0,
        show_value=False,
        max_width=350,
        # margin=(4, 10, 0, 10),
    )
    smooth_input = NumericInput(value=smooth_number)
    smooth_callback = CustomJS(
        args=dict(
            model_dict=model_dict,
            n_labels=len(split),
            checkbox=smooth_checkbox,
            input=smooth_input,
            slider=smooth_slider,
        ),
        code=open(
            os.path.join(
                os.path.dirname(__file__), '../static/js/plotjs', 'smooth_spectra.js'
            )
        ).read(),
    )
    smooth_checkbox.js_on_click(smooth_callback)
    smooth_input.js_on_change('value', smooth_callback)
    # smooth_slider.js_on_change('value', smooth_callback)
    smooth_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': smooth_slider, 'input': smooth_input},
            code="""
                    input.value = slider.value;
                    input.change.emit();
                """,
        ),
    )
    smooth_column = column(
        smooth_checkbox,
        smooth_slider,
        smooth_input,
        width=width if "mobile" in device else int(width * 1 / 5) - 20,
        margin=(4, 10, 0, 10),
    )

    # 20 is for padding
    slider_width = width if "mobile" in device else int(width * 2 / 5) - 20
    z_title = Div(text="Redshift (<i>z</i>): ")
    z_slider = Slider(
        value=obj.redshift if obj.redshift is not None else 0.0,
        start=0.0,
        end=3.0,
        step=0.001,
        show_value=False,
        format="0[.]000",
    )
    z_textinput = TextInput(
        value=str(obj.redshift if obj.redshift is not None else 0.0)
    )
    z_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': z_slider, 'textinput': z_textinput},
            code="""
                    textinput.value = parseFloat(slider.value).toFixed(3);
                    textinput.change.emit();
                """,
        ),
    )
    z = column(
        z_title,
        z_slider,
        z_textinput,
        width=slider_width,
        margin=(4, 10, 0, 10),
    )

    v_title = Div(text="<i>V</i><sub>expansion</sub> (km/s): ")
    v_exp_slider = Slider(
        value=0.0,
        start=0.0,
        end=3e4,
        step=10.0,
        show_value=False,
    )
    v_exp_textinput = TextInput(value='0')
    v_exp_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': v_exp_slider, 'textinput': v_exp_textinput},
            code="""
                    textinput.value = parseFloat(slider.value).toFixed(0);
                    textinput.change.emit();
                """,
        ),
    )
    v_exp = column(
        v_title,
        v_exp_slider,
        v_exp_textinput,
        width=slider_width,
        margin=(0, 10, 0, 10),
    )

    # Track elements that need to be shifted with change in z / v
    shifting_elements = []
    renderers = []
    for i, (name, (wavelengths, color)) in enumerate(SPEC_LINES.items()):

        if name in ('Tellurics-1', 'Tellurics-2'):
            el_data = pd.DataFrame(
                {
                    'name': name,
                    'wavelength': [(wavelengths[0] + wavelengths[1]) / 2],
                    'bandwidth': [wavelengths[1] - wavelengths[0]],
                }
            )
            new_line = plot.vbar(
                x='wavelength',
                width='bandwidth',
                top=ymax,
                color=color,
                source=ColumnDataSource(el_data),
                alpha=0.3,
            )

        else:
            flux_values = list(np.linspace(ymin, ymax, 100))
            flux_values[-1] = np.nan
            wavelength_values = [
                w for w in wavelengths for _ in flux_values
            ]  # repeat each wavelength 100 times
            el_data = pd.DataFrame(
                {
                    'name': name,
                    'x': wavelength_values,
                    'wavelength': wavelength_values,
                    'flux': [f for _ in wavelengths for f in flux_values],
                }
            )
            new_line = plot.line(
                x='x',
                y='flux',
                color=color,
                line_alpha=0.3,
                source=ColumnDataSource(el_data),
            )

        new_line.visible = False
        model_dict[f'element_{i}'] = new_line
        renderers.append(new_line)

        if name not in ('Sky Lines', 'Tellurics-1', 'Tellurics-2'):
            shifting_elements.append(new_line)
            new_line.glyph.line_alpha = 1.0

    # add the elemental lines to hover tool
    hover_lines = HoverTool(
        tooltips=[
            ('name', '@name'),
            ('wavelength', '@wavelength{0,0}'),
        ],
        renderers=renderers,
    )

    plot.add_tools(hover_lines)

    # Split spectral line legend into columns
    if device == "mobile_portrait":
        columns = 3
    elif device == "mobile_landscape":
        columns = 5
    else:
        columns = 7

    # Create columns from a list.
    #
    # `list(zip_longest(a, b, c, ...))` returns a tuple where the i-th
    # element comes from the i-th iterable argument.
    #
    # The trick here is to pass in the same iterable `column` times.
    # This gives us rows.
    rows = itertools.zip_longest(*[iter(SPEC_LINES.items())] * columns)

    # To form columns from the rows, zip the rows together.
    element_dicts = zip(*rows)

    all_column_checkboxes = []

    for column_idx, element_dict in enumerate(element_dicts):
        element_dict = [e for e in element_dict if e is not None]
        labels = [name for name, _ in element_dict]
        colors = [color for name, (wavelengths, color) in element_dict]
        column_checkboxes = CheckboxWithLegendGroup(
            labels=labels, active=[], colors=colors, width=width // (columns + 1)
        )
        all_column_checkboxes.append(column_checkboxes)

        callback_toggle_lines = CustomJS(
            args={'column_checkboxes': column_checkboxes, **model_dict},
            code=f"""
                    for (let i = 0; i < {len(labels)}; i = i + 1) {{
                        let el_idx = i * {columns} + {column_idx};
                        let el = eval("element_" + el_idx);
                        el.visible = (column_checkboxes.active.includes(i))
                    }}
                """,
        )
        column_checkboxes.js_on_click(callback_toggle_lines)

    # Move spectral lines when redshift or velocity changes
    speclines = {f'specline_{i}': line for i, line in enumerate(shifting_elements)}
    callback_zvs = CustomJS(
        args={'z': z_textinput, 'v_exp': v_exp_textinput, **speclines},
        code=f"""
                const c = 299792.458; // speed of light in km / s
                for (let i = 0; i < {len(speclines)}; i = i + 1) {{
                    let el = eval("specline_" + i);
                    el.data_source.data.x = el.data_source.data.wavelength.map(
                        x_i => (x_i * (1 + parseFloat(z.value)) /
                                        (1 + parseFloat(v_exp.value) / c))
                    );
                    el.data_source.change.emit();
                }}
            """,
    )

    # Hook up callback that shifts spectral lines when z or v changes
    z_textinput.js_on_change('value', callback_zvs)
    v_exp_textinput.js_on_change('value', callback_zvs)

    z_textinput.js_on_change(
        'value',
        CustomJS(
            args={'z': z_textinput, 'slider': z_slider},
            code="""
                    // Update slider value to match text input
                    slider.value = parseFloat(z.value).toFixed(3);
                """,
        ),
    )

    v_exp_textinput.js_on_change(
        'value',
        CustomJS(
            args={'slider': v_exp_slider, 'v_exp': v_exp_textinput},
            code="""
                    // Update slider value to match text input
                    slider.value = parseFloat(v_exp.value).toFixed(3);
                """,
        ),
    )

    row2 = row(all_column_checkboxes)
    row3 = (
        column(z, v_exp, smooth_column)
        if "mobile" in device
        else row(z, v_exp, smooth_column)
    )
    return column(
        plot,
        row2,
        row3,
        sizing_mode='stretch_width',
        width=width,
        height=height,
    )


def get_dimensions_by_device(device, width):
    frame_width = width - 64
    aspect_ratio = 2.0
    legend_row_height = 25
    legend_items_per_row = 1
    if device == "mobile_portrait":
        legend_items_per_row = 1
        legend_row_height = 24
        aspect_ratio = 1
    elif device == "mobile_landscape":
        legend_items_per_row = 4
        legend_row_height = 50
        aspect_ratio = 1.8
    elif device == "tablet_portrait":
        legend_items_per_row = 5
        legend_row_height = 50
        aspect_ratio = 1.5
    elif device == "tablet_landscape":
        legend_items_per_row = 7
        legend_row_height = 50
        aspect_ratio = 1.8
    elif device == "browser":
        frame_width = width - 200
        aspect_ratio = 2.0
        legend_row_height = 25
        legend_items_per_row = 1

    return frame_width, aspect_ratio, legend_row_height, legend_items_per_row

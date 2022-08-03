import copy
import itertools
import math
import json
import collections

import numpy as np
import pandas as pd
from sqlalchemy.orm import joinedload

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
    Dropdown,
    Spinner,
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
    Obj,
    Annotation,
    AnnotationOnSpectrum,
    Photometry,
    Instrument,
    PHOT_ZP,
    Spectrum,
    User,
)

from .enum_types import ALLOWED_SPECTRUM_TYPES

# use the full registry from the enum_types import of sykportal
# which may have custom bandpasses
from .enum_types import sncosmo as snc


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
        bandpass = snc.get_bandpass(bandpass_name)
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

    Returns
    -------
    None
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


def get_photometry_button_callback(info, model_dict):
    """Get the callback function for a photometry button for showing photometry
    points

    Parameters
    ----------
    info : dict
        Dictionary including the filters and origins that should be turned visible
        on click of this photometry button.
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.

    Returns
    -------
    CustomJS defining the callback
    """
    return CustomJS(
        args={'info': info, 'model_dict': model_dict},
        code="""
        for (const [key, value] of Object.entries(model_dict)) {
          const [filter, origin, extra] = key.split("~");
          if (info['filters'].includes(filter) || info['origins'].includes(origin)) {
            value.visible = true;
          }
        }
        """,
    )


def make_hide_photometry_button(model_dict):
    """Make a button to hide photometry on the photometry plot.

    Parameters
    ----------
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.

    Returns
    -------
    bokeh Button object
    """
    button = Button(
        name="Hide All Photometry", label="Hide All Photometry", width_policy="min"
    )
    callback_hide_photometry = CustomJS(
        args={'model_dict': model_dict},
        code="""
        for (const [key, value] of Object.entries(model_dict)) {
            value.visible = false
        }
        """,
    )
    button.js_on_click(callback_hide_photometry)
    return button


def make_show_all_photometry_button(model_dict):
    """Make a button to show all photometry on the photometry plot.

    Parameters
    ----------
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.

    Returns
    -------
    bokeh Button object
    """
    button = Button(
        name="Show All Photometry", label="Show All Photometry", width_policy="min"
    )
    callback_show_photometry = CustomJS(
        args={'model_dict': model_dict},
        code="""
        for (const [key, value] of Object.entries(model_dict)) {
            value.visible = true
        }
        """,
    )
    button.js_on_click(callback_show_photometry)
    return button


def make_show_and_hide_photometry_buttons(model_dict, user, device):
    """Make a container for the show and hide photometry buttons.

    Parameters
    ----------
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    user : User object
        Current user.
    device : str
        String representation of device being used by the user. Contains "browser",
        "mobile", or "tablet"

    Returns
    -------
    bokeh row object
    """
    buttons = [
        make_show_all_photometry_button(model_dict),
        make_hide_photometry_button(model_dict),
    ]
    if user.preferences and "photometryButtons" in user.preferences:
        for name, info in user.preferences["photometryButtons"].items():
            btn = Button(label=f"Show {name}", width_policy="min")
            btn.js_on_click(get_photometry_button_callback(info, model_dict))
            buttons.append(btn)
    if "mobile" in device:
        return column(buttons)
    # if not on mobile, return a column of rows with 5 buttons in each row.
    return column([row(buttons[i : i + 5]) for i in range(0, len(buttons), 5)])


def add_axis_labels(plot, panel_name):
    """Add axis labels to a photometry plot.

    Parameters
    ----------
    plot : bokeh Figure object
        Figure object that axis labels should be added to
    panel_name : str
        Name of the panel. One of flux, mag or period

    Returns
    -------
    None

    """
    axis_label_dict = {
        'flux': {'x': 'MJD', 'y': 'Flux (μJy)'},
        'mag': {'x': 'MJD', 'y': 'AB mag'},
        'period': {'x': 'phase', 'y': 'mag'},
    }
    plot.xaxis.axis_label = axis_label_dict[panel_name]['x']
    plot.yaxis.axis_label = axis_label_dict[panel_name]['y']


def check_visibility_on_phot_plot(user, show_all_filters, show_all_origins, label):
    """Function to check if a photometry point should be displayed on the plot in
    accordance with the user's photometry plotting preferences.

    Parameters
    ----------
    user : User object
        Current user
    show_all_filters: Boolean
        Boolean value indicating whether to show all filters or not. Set to true
        when the plot does not contain any of the user's automatically visible filters
        as set in the preferences.
    show_all_origins: Boolean
        Boolean value indicating whether to show all origins or not. Set to true
        when the plot does not contain any of the user's automatically visible
        origins as set in the preferences.
    label : str
        Label of the photometry containing instrument, filter, and origin such as
        'ZTF/ztfg/Muphoten'

    Returns
    -------
    visible : boolean
        Boolean value indicating whether the point should be visible or not.
    """
    if show_all_filters and show_all_origins:
        return True
    split = label.split('/')
    filter = split[1]
    origin = None
    if len(split) == 3:
        origin = split[2]
    visible = False
    if user.preferences:
        if (
            ("automaticallyVisibleFilters" in user.preferences)
            and (filter in user.preferences['automaticallyVisibleFilters'])
        ) or (
            origin
            and ('automaticallyVisibleOrigins' in user.preferences)
            and (origin in user.preferences['automaticallyVisibleOrigins'])
        ):
            visible = True
    return visible


def make_scatter(
    plot,
    model_dict,
    name,
    i,
    label,
    data_source,
    x,
    y,
    renderers,
    imhover,
    spinner,
    color_dict,
    markers,
    instruments,
    user,
    show_all_filters,
    show_all_origins,
):
    """Adds a scatter plot to a bokeh Figure object.

    Parameters
    ----------
    plot : bokeh Figure object
        Figure object that scatter plot should be added to
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    name : str
        Short name describing the scatter points such as 'obs', 'unobs', or 'bin'
    i : int
        Index of the loop that iterates over all the separate photometry. Used to
        keep track of which photometry point the GlyphRenderer belongs to
    label : str
        Label of the photometry containing instrument, filter, and origin such as
        'ZTF/ztfg/Muphoten'
    data_source : bokeh ColumnDataSource object
        ColumnDataSource used for plot.scatter
    x : str
        x name like 'mjd'
    y : str
        y name like 'lim_mag'
    renderers : list
        List of renderers for the current legend item. This scatter plot
        GlyphRenderer is added to the renderers.
    imhover : HoverTool object
        HoverTool for current photometry
    spinner : Spinner object
        Spinner for controlling the data size of photometry points.
    color_dict : dict
        Dictionary defining which color the data points should be
    markers : list
        List of marker shapes
    instruments : list
        List of instruments
    user : User object
        Current user.
    show_all_filters: Boolean
        Boolean value indicating whether to show all filters or not. Set to true
        when the plot does not contain any of the user's automatically visible
        filters as set in the preferences.
    show_all_origins: Boolean
        Boolean value indicating whether to show all origins or not. Set to
        true when the plot does not contain any of the user's automatically
        visible origins as set in the preferences.

    Returns
    -------
    None
    """
    split = label.split('/')
    key = f'{split[1]}~{split[2] if len(split) == 3 else "None"}~{name}{i}'
    size = 4
    if user.preferences and "photometryDataPointSize" in user.preferences:
        size = int(user.preferences["photometryDataPointSize"])
    visible = check_visibility_on_phot_plot(
        user, show_all_filters, show_all_origins, label
    )
    model_dict[key] = plot.scatter(
        x=x,
        y=y,
        size=size,
        visible=visible,
        color=color_dict,
        marker=factor_mark('instrument', markers, instruments),
        fill_alpha=0.1,
        line_color=color_dict,
        fill_color=color_dict,
        source=data_source,
    )
    renderers.append(model_dict[key])
    imhover.renderers.append(model_dict[key])
    spinner.js_link('value', model_dict[key].glyph, 'size')


def make_multi_line(
    plot,
    model_dict,
    name,
    i,
    label,
    data_source,
    renderers,
    user,
    show_all_filters,
    show_all_origins,
):
    """Adds a multi-line plot to a bokeh Figure object.

    Parameters
    ----------
    plot : bokeh Figure object
        Figure object that multi-line plot should be added to
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    name : str
        Short name describing the scatter points such as 'obs', 'unobs', or 'bin'
    i : int
        Index of the loop that iterates over all the separate photometry. Used to
        keep track of which photometry point the GlyphRenderer belongs to
    label : str
        Label of the photometry containing instrument, filter, and origin such as
        'ZTF/ztfg/Muphoten'
    data_source : bokeh ColumnDataSource object
        ColumnDataSource used for plot.scatter
    renderers : list
        List of renderers for the current legend item. This scatter plot
        GlyphRenderer is added to the renderers.
    user : User object
        Current user.
    show_all_filters: Boolean
        Boolean value indicating whether to show all filters or not. Set to true
         when the plot does not contain any of the user's automatically visible
         filters as set in the preferences.
    show_all_origins: Boolean
        Boolean value indicating whether to show all origins or not. Set to true
        when the plot does not contain any of the user's automatically visible
        origins as set in the preferences.

    Returns
    -------
    None
    """
    split = label.split('/')
    key = f'{split[1]}~{split[2] if len(split) == 3 else "None"}~{name}{i}'
    visible = check_visibility_on_phot_plot(
        user, show_all_filters, show_all_origins, label
    )
    model_dict[key] = plot.multi_line(
        xs='xs',
        ys='ys',
        visible=visible,
        color='color',
        source=data_source,
    )
    renderers.append(model_dict[key])


def get_errs(panel_name, df, ph=''):
    """Gets the errors for a certain panel. Used to make the error lines on the data
    points.

    Parameters
    ----------
    panel_name : str
        Name of the panel. One of 'mag', 'flux', and 'period'
    df : pandas DataFrame object
        Photometry data
    ph : Optional str
        Only used with the period panel. ph is 'a' or 'b'

    Returns
    -------
    Tuple containing the x and y errors
    """
    df = df if panel_name == 'flux' else df[df['obs']]
    err_dict = {
        'mag': {'px': 'mjd', 'py': 'mag', 'err': 'magerr'},
        'flux': {'px': 'mjd', 'py': 'flux', 'err': 'fluxerr'},
        'period': {'px': f'mjd_fold{ph}', 'py': 'mag', 'err': 'magerr'},
    }
    y_err_x = []
    y_err_y = []
    for d, ro in df.iterrows():
        px = ro[err_dict[panel_name]['px']]
        py = ro[err_dict[panel_name]['py']]
        err = ro[err_dict[panel_name]['err']]

        y_err_x.append((px, px))
        y_err_y.append((py - err, py + err))
    return (y_err_x, y_err_y)


def mark_detections(plot, detection_dates, ymin, ymax):
    """Mark detection lines on a plot

    Parameters
    ----------
    plot : bokeh Figure object
    detections_date : pandas Series object
        The detections dates to be plotted as lines
    ymin : int
        Minimum y range value of the plot
    ymax : int
        Maximum y range value of the plot

    Returns
    -------
    None
    """
    first = round(detection_dates.min(), 6)
    last = round(detection_dates.max(), 6)
    first_color = "#34b4eb"
    last_color = "#8992f5"
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


def get_show_all_flag(user, data, type):
    """Return a flag of whether to show all photometry points of a certain type on the phot plot.

    Parameters
    ----------
    user : User object
        Current user.
    data : pandas DataFrame object
        Photometry data (ungrouped)
    type : str
        Thing we're filtering the photometry by. Currently one of 'filters' or 'origins'.

    Returns
    -------
    boolean flag for show all.
    """
    # The purpose of the boolean flag is for the case where the plot contains none of the user's automatically visible filters
    # /origins: in that case we will display all of the photometry points and set show_all_filters/origins to `True`. Otherwise, we
    # would like to selectively display points based on the user's preferences, so the flags will be set to `False`.
    unique_values = list(data[type[:-1]].unique())
    if 'None' in unique_values:
        unique_values.remove('None')
    show_all = True
    if user.preferences:
        if f"automaticallyVisible{type.capitalize()}" in user.preferences:
            for value in user.preferences[f'automaticallyVisible{type.capitalize()}']:
                if value in unique_values:
                    show_all = False
                    break
    return show_all


def make_legend_items_and_detection_lines(
    grouped_data,
    plot,
    spinner,
    model_dict,
    imhover,
    panel_name,
    color_dict,
    y_range,
    data,
    obsind,
    markers,
    instruments,
    period,
    user,
):
    """Makes the legend items for a plot and adds detections lines.

    Parameters
    ----------
    grouped_data : pandas DataFrameGroupBy object
        The photometry data grouped by label.
    plot : bokeh Figure object
    spinner : Spinner object
        Spinner for controlling the data size of photometry points.
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    imhover : HoverTool object
        HoverTool for current photometry
    panel_name : str
        Name of the panel. One of 'flux', 'mag' or 'period'
    color_dict : dict
        Dictionary defining which color the data points should be
    y_range : tuple(int)
        Tuple containing the minimum and maximum y range values of the plot
        respectively
    data : pandas DataFrame object
        Photometry data (ungrouped)
    obsind : pandas Series object
        Index of points that have been positively detected (observed),
        i.e., points that are not upper limits.
    markers : list
        List of marker shapes
    instruments : list
        List of instruments
    period : float
        period used for manipulating the data frame
    user : User object
        Current user.

    Returns
    -------
    List of LegendItem objects
    """

    empty_data_source = dict(
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

    show_all_filters = get_show_all_flag(user, data, 'filters')
    show_all_origins = get_show_all_flag(user, data, 'origins')

    legend_items = []
    for i, (label, df) in enumerate(grouped_data):
        renderers = []
        unobs_source = df[~df['obs']].copy()
        unobs_source.loc[:, 'alpha'] = 0.8
        if panel_name == 'flux':
            df = df[df['hasflux']]
        elif panel_name == 'period':
            df['mjd_folda'] = (df['mjd'] % period) / period
            df['mjd_foldb'] = df['mjd_folda'] + 1.0
        if panel_name == 'mag' or panel_name == 'flux':
            y_err_x, y_err_y = get_errs(panel_name, df)
            plotting_dict = {
                'mag': {
                    'scatter': {
                        'unobs': {
                            'x': 'mjd',
                            'y': 'lim_mag',
                            'data_source': unobs_source,
                        },
                        'obs': {'x': 'mjd', 'y': 'mag', 'data_source': df[df['obs']]},
                        'bin': {
                            'x': 'mjd',
                            'y': 'mag',
                            'data_source': empty_data_source,
                        },
                        'unobsbin': {
                            'x': 'mjd',
                            'y': 'lim_mag',
                            'data_source': empty_data_source,
                        },
                    }
                },
                'flux': {
                    'scatter': {
                        'obs': {'x': 'mjd', 'y': 'flux', 'data_source': df},
                        'bin': {
                            'x': 'mjd',
                            'y': 'flux',
                            'data_source': empty_data_source,
                        },
                    }
                },
            }
            for name, values in plotting_dict[panel_name]['scatter'].items():
                if name == 'unobs':
                    markers = ['inverted_triangle']
                else:
                    markers = ['circle']
                make_scatter(
                    plot,
                    model_dict,
                    name,
                    i,
                    label,
                    ColumnDataSource(values['data_source']),
                    values['x'],
                    values['y'],
                    renderers,
                    imhover,
                    spinner,
                    color_dict,
                    markers,
                    instruments,
                    user,
                    show_all_filters,
                    show_all_origins,
                )
            make_multi_line(
                plot,
                model_dict,
                'obserr',
                i,
                label,
                ColumnDataSource(
                    data=dict(
                        xs=y_err_x,
                        ys=y_err_y,
                        color=df['color']
                        if panel_name == 'flux'
                        else df[df['obs']]['color'],
                        alpha=[1.0]
                        * len(df if panel_name == 'flux' else df[df['obs']]),
                    )
                ),
                renderers,
                user,
                show_all_filters,
                show_all_origins,
            )
            make_multi_line(
                plot,
                model_dict,
                'binerr',
                i,
                label,
                ColumnDataSource(data=dict(xs=[], ys=[], color=[])),
                renderers,
                user,
                show_all_filters,
                show_all_origins,
            )
        elif panel_name == 'period':
            for ph in ['a', 'b']:
                y_err_x, y_err_y = get_errs(panel_name, df, ph)
                make_scatter(
                    plot,
                    model_dict,
                    f'fold{ph}',
                    i,
                    label,
                    ColumnDataSource(df[df['obs']]),
                    f'mjd_fold{ph}',
                    'mag',
                    renderers,
                    imhover,
                    spinner,
                    color_dict,
                    markers,
                    instruments,
                    user,
                    show_all_filters,
                    show_all_origins,
                )
                make_multi_line(
                    plot,
                    model_dict,
                    f'fold{ph}err',
                    i,
                    label,
                    ColumnDataSource(
                        data=dict(
                            xs=y_err_x,
                            ys=y_err_y,
                            color=df[df['obs']]['color'],
                            alpha=[1.0] * len(df[df['obs']]),
                        )
                    ),
                    renderers,
                    user,
                    show_all_filters,
                    show_all_origins,
                )
        else:
            raise ValueError("Panel name should be one of mag, flux, and period.")
        if panel_name == 'mag' or panel_name == 'flux':
            mark_detections(
                plot,
                data[obsind]['mjd']
                if panel_name == 'mag'
                else data[data['hasflux']]['mjd'],
                y_range[0],
                y_range[1],
            )
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

    return legend_items


def transformed_model_dict(model_dict):
    """In order to programmatically toggle visibilty, the model_dict keys are altered to contain the filter, instrument, and origin of
    the photometry point. However, many widgets need the original model dict with keys such as obs0 and bin0 in order to work correctly.
    This function changes the keys of the model dict to work with that format.

    Parameters
    ----------
    model_dict : dict
        Dictionary with string keys and GlyphRenderer values.

    Returns
    -------
    dict with transformed keys.
    """
    transformed_model_dict = {}
    for k, v in model_dict.items():
        label = k.split('~')[2] if '~' in k else k
        transformed_model_dict[label] = v
    return transformed_model_dict


def make_binsize_slider(grouped_data, model_dict):
    """Makes a slider to control binsize.

    Parameters
    ----------
    grouped_data : pandas DataFrameGroupBy object
        The photometry data grouped by label.
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.

    Returns
    -------
    bokeh Slider object
    """
    model_dict = transformed_model_dict(model_dict)
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
        args={'slider': slider, 'n_labels': len(grouped_data), **model_dict},
        code=open(
            os.path.join(os.path.dirname(__file__), '../static/js/plotjs', 'stackm.js')
        )
        .read()
        .replace('default_zp', str(PHOT_ZP))
        .replace('detect_thresh', str(PHOT_DETECTION_THRESHOLD)),
    )
    slider.js_on_change('value', callback)
    return slider


def make_export_csv_button(grouped_data, model_dict, obj_id):
    """Makes a button to export a bold light curve to CSV.

    Parameters
    ----------
    grouped_data : pandas DataFrameGroupBy object
        The photometry data grouped by label.
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    obj_id : str
        ID of the object

    Returns
    -------
    bokeh Button object
    """
    model_dict = transformed_model_dict(model_dict)
    button = Button(label="Export Bold Light Curve to CSV")
    button.js_on_click(
        CustomJS(
            args={'n_labels': len(grouped_data), **model_dict},
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
    return button


def make_period_controls(
    period_labels,
    period_list,
    period,
    grouped_data,
    plot,
    model_dict,
    device,
    width,
    layout,
):
    """Makes period controls to be used in a period photometry panel.

    Parameters
    ----------
    period_labels : list
        List of labels for the period buttons.
    period_list : list
        List of periods for the period buttons.
    period : float
        The current period.
    grouped_data : pandas DataFrameGroupBy object
        The photometry data grouped by label.
    plot : bokeh Plot object
        The plot object.
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    device : str
        The device to use for the plot.
    width : int
        The width of the plot.
    layout : bokeh Layout object
        The layout object.

    Returns
    -------
    bokeh column object
    """
    model_dict = transformed_model_dict(model_dict)
    period_selection = RadioGroup(labels=period_labels, active=0)

    phase_selection = RadioGroup(labels=["One phase", "Two phases"], active=1)
    period_title = Div(text="Period (days): ")
    period_textinput = TextInput(value=str(period if period is not None else 0.0))
    period_textinput.js_on_change(
        'value',
        CustomJS(
            args={
                'textinput': period_textinput,
                'numphases': phase_selection,
                'n_labels': len(grouped_data),
                'p': plot,
                **model_dict,
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
                'n_labels': len(grouped_data),
                'p': plot,
                **model_dict,
            },
            code=open(
                os.path.join(
                    os.path.dirname(__file__), '../static/js/plotjs', 'foldphase.js'
                )
            ).read(),
        )
    )
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
    return period_controls


def add_widgets(
    panel_name,
    layout,
    grouped_data,
    model_dict,
    obj_id,
    period_labels,
    period_list,
    period,
    plot,
    device,
    width,
):
    """Adds widgets to the layout of a photometry panel.

    Parameters
    ----------
    panel_name : str
        Name of the panel. One of 'mag', 'flux', and 'period'. Used to determine
        which
        widgets to add.
    layout : bokeh column object
        The layout of the panel. Widgets added to this object.
    grouped_data : pandas DataFrameGroupBy object
        The photometry data grouped by label.
    model_dict : dict
        A dictionary containing all of the GlyphRenderers for the plot.
    obj_id : int
        ID of the source/object the photometry is for
    period_labels, period_list, period : list, list, float
        Information needed for the period controls
    plot : bokeh Figure object
    device : str
        String representation of device being used by the user. Contains "browser",
        "mobile", or "tablet"
    width : int
        Width of the plot

    Returns
    -------
    None
    """
    if panel_name == 'mag':
        slider = make_binsize_slider(grouped_data, model_dict)
        export_csv_button = make_export_csv_button(grouped_data, model_dict, obj_id)
        top_layout = (
            slider
            if "mobile" in device or "tablet" in device
            else row(slider, export_csv_button)
        )
        layout.children.insert(0, top_layout)
    elif panel_name == 'flux':
        slider = make_binsize_slider(grouped_data, model_dict)
        layout.children.insert(0, slider)
    elif panel_name == 'period':
        period_controls = make_period_controls(
            period_labels,
            period_list,
            period,
            grouped_data,
            plot,
            model_dict,
            device,
            width,
            layout,
        )
        layout.children.insert(2, period_controls)
    else:
        raise ValueError("Panel name should be one of mag, flux, and period.")


def make_photometry_panel(
    panel_name, device, width, user, data, obj_id, spectra, session
):
    """Makes a panel for the photometry plot.

    Parameters
    ----------
    panel_name : str
        Name of the panel. One of 'mag', 'flux', and 'period'
    device : str
        String representation of device being used by the user. Contains "browser",
        "mobile", or "tablet"
    width : int
        Width of the plot
    user : User object
        Current user.
    data : pandas DataFrame object
        Photometry data
    obj_id : int
        ID of the source/object the photometry is for
    spectra : list of Spectra objects
        The source/object's spectra
    session: sqlalchemy.Session
        Database session for this transaction

    Returns
    -------
    bokeh Panel object or None if the panel should
    not be added to the plot (i.e. no period plot)
    """

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

    grouped_data = data.groupby('label', sort=False)

    finite = np.isfinite(data['flux'])
    fdata = data[finite]
    lower = np.min(fdata['flux']) * 0.95
    upper = np.max(fdata['flux']) * 1.05

    xmin = data['mjd'].min() - 2
    xmax = data['mjd'].max() + 2
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
        + legend_row_height * int(len(grouped_data) / legend_items_per_row)
        + 30  # 30 is the height of the toolbar
    )
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

    ranges = {
        'mag': {'y_range': (ymax, ymin), 'x_range': (xmin, xmax)},
        'flux': {'y_range': (lower, upper), 'x_range': (xmin, xmax)},
        'period': {'y_range': (ymax, ymin), 'x_range': (-0.01, 2.01)},
    }

    y_range = ranges[panel_name]['y_range']
    x_range = ranges[panel_name]['x_range']

    plot = figure(
        frame_width=frame_width,
        height=height,
        active_drag=active_drag,
        tools=tools,
        y_range=y_range,
        x_range=x_range,
        toolbar_location='above',
        toolbar_sticky=True,
        x_axis_location='below' if panel_name == 'period' else 'above',
        sizing_mode="stretch_width",
    )
    add_axis_labels(plot, panel_name)
    plot.toolbar.logo = None
    if device == "mobile_portrait":
        plot.xaxis.ticker.desired_num_ticks = 5

    if panel_name == 'mag' or panel_name == 'flux':
        now = Time.now().mjd
        plot.extra_x_ranges = {
            "Days Ago": Range1d(start=now - x_range[0], end=now - x_range[1])
        }
        plot.add_layout(
            LinearAxis(x_range_name="Days Ago", axis_label="Days Ago"), 'below'
        )

    obj = session.scalars(
        Obj.select(session.user_or_token).where(Obj.id == obj_id)
    ).first()
    if obj.dm is not None:
        plot.extra_y_ranges = {
            "Absolute Mag": Range1d(start=y_range[0] - obj.dm, end=y_range[1] - obj.dm)
        }
        plot.add_layout(
            LinearAxis(y_range_name="Absolute Mag", axis_label="m - DM"), 'right'
        )
    period_labels = []
    period_list = []
    period = None
    if panel_name == 'period':
        annotation_list = session.scalars(
            Annotation.select(session.user_or_token).where(Annotation.obj_id == obj.id)
        ).all()
        for an in annotation_list:
            if 'period' in an.data:
                period_list.append(an.data['period'])
                period_labels.append(an.origin + ": %.9f" % an.data['period'])

        if len(period_list) > 0:
            period = period_list[0]
        else:
            period = None
            return None

    imhover = HoverTool(tooltips=tooltip_format)
    imhover.renderers = []
    plot.add_tools(imhover)

    model_dict = {}
    spinner = Spinner(
        title="Data point size",
        low=1,
        high=60,
        step=0.5,
        value=(
            user.preferences['photometryDataPointSize']
            if user.preferences and 'photometryDataPointSize' in user.preferences
            else 4
        ),
        width_policy="min",
    )
    spinner.js_on_change(
        'value',
        CustomJS(
            args=dict(spinner=spinner),
            code=open(
                os.path.join(
                    os.path.dirname(__file__),
                    '../static/js/plotjs',
                    'update_data_point_size.js',
                )
            ).read(),
        ),
    )

    legend_items = make_legend_items_and_detection_lines(
        grouped_data,
        plot,
        spinner,
        model_dict,
        imhover,
        panel_name,
        color_dict,
        y_range,
        data,
        obsind,
        markers,
        instruments,
        period,
        user,
    )

    add_plot_legend(plot, legend_items, width, legend_orientation, legend_loc)

    if panel_name == 'mag' or panel_name == 'flux':
        annotate_spec(plot, spectra, y_range[0], y_range[1])

    layout = column(
        plot,
        column(
            make_show_and_hide_photometry_buttons(model_dict, user, device), spinner
        ),
        # width=width,
    )
    add_widgets(
        panel_name,
        layout,
        grouped_data,
        model_dict,
        obj_id,
        period_labels,
        period_list,
        period,
        plot,
        device,
        width,
    )
    return Panel(child=layout, title=panel_name.capitalize())


def photometry_plot(obj_id, user_id, session, width=600, device="browser"):
    """Create object photometry scatter plot.

    Parameters
    ----------
    obj_id : str
        ID of Obj to be plotted.
    user_id : User object ID
        Current user ID.
    session: sqlalchemy.Session
        Database session for this transaction
    width : int
        Width of the plot
    device : str
        String representation of device being used by the user. Contains "browser",
        "mobile", or "tablet"

    Returns
    -------
    dict
        Returns Bokeh JSON embedding for the desired plot.
    """

    data = session.scalars(
        Photometry.select(session.user_or_token)
        .options(joinedload(Photometry.instrument).joinedload(Instrument.telescope))
        .where(Photometry.obj_id == obj_id)
    ).all()

    query_result = []
    for p in data:
        telescope = p.instrument.telescope.nickname
        instrument = p.instrument.name
        result = p.to_dict()
        result['telescope'] = telescope
        result['instrument'] = instrument
        query_result.append(result)

    data = pd.DataFrame.from_dict(query_result)
    if data.empty:
        return None, None, None

    user = session.scalars(
        User.select(session.user_or_token).where(User.id == user_id)
    ).first()

    spectra = (
        session.scalars(
            Spectrum.select(session.user_or_token).where(Spectrum.obj_id == obj_id)
        )
        .unique()
        .all()
    )

    data['effwave'] = [get_effective_wavelength(f) for f in data['filter']]
    data['color'] = [get_color(w) for w in data['effwave']]

    data.sort_values(by=['effwave'], inplace=True)

    # labels for legend items
    labels = []
    for i, datarow in data.iterrows():
        label = f'{datarow["instrument"]}/{datarow["filter"]}'
        if datarow['origin'] != 'None':
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

    panel_names = ['mag', 'flux', 'period']
    panels = []

    for panel_name in panel_names:
        panel = make_photometry_panel(
            panel_name, device, width, user, data, obj_id, spectra, session
        )
        if panel:
            panels.append(panel)
    tabs = Tabs(
        tabs=panels,
        # width=width,
    )
    try:
        return bokeh_embed.json_item(tabs)
    except ValueError:
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print('PHOTOMETRY PLOT FAILED ON THIS DATASET')
            print(data)
        return Tabs()


def smoothing_function(values, window_size):
    """
    Smooth the input "values" using a rolling average
    where "window_size" is the number of points to use
    for averaging.
    This should be the same logic as static/js/plotjs/smooth_spectra.js

    Parameters
    ----------
    values : float array or list of floats
        array of flux values to be smoothed.
    window_size : integer scalar
        the number of points to be used as the smoothing window.

    Returns
    -------
    float array
        the flux values after smoothing. Same size as "values".
    """

    if values is None or not hasattr(values, '__len__') or len(values) == 0:
        return values
    output = np.zeros(values.shape)
    under = int((window_size + 1) // 2) - 1
    over = int(window_size // 2)

    for i in range(len(values)):
        idx_low = i - under if i - under >= 0 else 0
        idx_high = i + over if i + over < len(values) else len(values) - 1
        N = 0
        for j in range(idx_low, idx_high):
            if np.isnan(values[j]) == 0:
                N += 1
                output[i] += values[j]
        output[i] /= N

    return output


def spectroscopy_plot(
    obj_id,
    session,
    spec_id=None,
    width=800,
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
    session: sqlalchemy.Session
        Database session for this transaction
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

    obj = session.scalars(
        Obj.select(session.user_or_token).where(Obj.id == obj_id)
    ).first()
    if obj is None:
        raise ValueError(f'Cannot find object with ID "{obj_id}"')
    spectra = (
        session.scalars(
            Spectrum.select(session.user_or_token).where(Spectrum.obj_id == obj_id)
        )
        .unique()
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
                session,
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

        height = None
        for layout in layouts:
            if layout.height is not None:
                height = layout.height + 60
                break

        tabs = Tabs(tabs=panels, width=width, height=height, sizing_mode='fixed')
        return bokeh_embed.json_item(tabs)

    return bokeh_embed.json_item(layouts[0])


def make_spectrum_layout(
    obj, spectra, session, device, width, smoothing, smooth_number
):
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
    session: sqlalchemy.Session
        Database session for this transaction
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
        annotations = session.scalars(
            AnnotationOnSpectrum.select(session.user_or_token).where(
                AnnotationOnSpectrum.spectrum_id == s.id
            )
        ).all()
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

    # https://docs.bokeh.org/en/latest/docs/user_guide/styling.html#setting-render-levels
    # image is the lowest render level in bokeh plots, set all of the grid lines to this lowest level
    # so we can use the 'underlay' and 'glyph' levels for the spectra.
    for grid in plot.grid:
        grid.level = "image"
    for grid in plot.xgrid:
        grid.level = "image"
    for grid in plot.ygrid:
        grid.level = "image"

    model_dict = {}
    legend_items = []
    label_dict = {}
    for i, (key, df) in enumerate(split):

        renderers = []
        s = next(spec for spec in spectra if spec.id == key)
        if s.label is not None and len(s.label) > 0:
            label = s.label
        else:
            label = f'{s.instrument.name} ({s.observed_at.date().strftime("%m/%d/%y")})'
        label_dict[str(s.id)] = i
        model_dict['s' + str(i)] = plot.step(
            x='wavelength',
            y='flux',
            color=color_map[key],
            source=ColumnDataSource(df),
        )
        renderers.append(model_dict[f's{i}'])

        # this starts out the same as the previous plot, but can be binned/smoothed later in JS
        dfs = copy.deepcopy(df)
        if smoothing:
            dfs['flux'] = smoothing_function(dfs['flux_original'], smooth_number)
        model_dict[f'bin{i}'] = plot.step(
            x='wavelength', y='flux', color=color_map[key], source=ColumnDataSource(dfs)
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

        legend_items.append(LegendItem(label=label, renderers=renderers, id=s.id))
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
        step=0.00001,
        show_value=False,
        format="0[.]0000",
    )
    z_input = NumericInput(
        value=obj.redshift if obj.redshift is not None else 0.0,
        mode='float',
    )
    z_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': z_slider, 'input': z_input},
            code="""
                    input.value = slider.value;
                    input.change.emit();
                """,
        ),
    )
    z = column(
        z_title,
        z_slider,
        z_input,
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
    v_exp_input = NumericInput(value=0, mode='int')
    v_exp_slider.js_on_change(
        'value',
        CustomJS(
            args={'slider': v_exp_slider, 'input': v_exp_input},
            code="""
                    input.value = slider.value;
                    input.change.emit();
                """,
        ),
    )
    v_exp = column(
        v_title,
        v_exp_slider,
        v_exp_input,
        width=slider_width,
        margin=(0, 10, 0, 10),
    )
    w_title = Div(text="Custom wavelength")
    w_input = NumericInput(
        value=0.0,
        mode='float',
    )

    # Track elements that need to be shifted with change in z / v
    shifting_elements = []
    renderers = []
    obj_redshift = 0 if obj.redshift is None else obj.redshift

    flux_values = list(np.linspace(ymin, ymax, 100))
    flux_values[-1] = np.nan
    wavelength_values = [w_input.value]
    el_data = pd.DataFrame(
        {
            'name': 'custom_wavelength_name',
            'x': wavelength_values,
            'wavelength': wavelength_values,
        }
    )
    # el_data['x'] = el_data['wavelength'] * (1.0 + obj_redshift)
    new_line_w = plot.vbar(
        x='x',
        width=10,
        top=ymax,
        line_alpha=0.3,
        source=ColumnDataSource(el_data),
    )

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
            if name != 'Sky Lines':
                el_data['x'] = el_data['wavelength'] * (1.0 + obj_redshift)
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

    new_line_w.visible = False
    model_dict['custom_line'] = new_line_w
    renderers.append(new_line_w)

    w_input.js_on_change(
        'value',
        CustomJS(
            args={'input': w_input, 'model_dict': model_dict},
            code="""
                    if (input.value === null) {
                        model_dict['custom_line'].visible = false;
                    }
                    else {
                        model_dict['custom_line'].data_source.data['x'][0] = input.value;
                        model_dict['custom_line'].visible = true;
                        model_dict['custom_line'].data_source.data['wavelength'][0] = input.value;
                        model_dict['custom_line'].data_source.change.emit();
                    }
                """,
        ),
    )
    w = column(
        w_title,
        w_input,
        width=width if "mobile" in device else int(width * 1 / 5) - 20,
        margin=(4, 10, 0, 10),
    )

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

    hide_all_spectra = Button(
        name="Hide All Spectra", label="Hide All Spectra", width_policy="min"
    )
    callback_hide_all_spectra = CustomJS(
        args={'model_dict': model_dict},
        code="""
            for (const[key, value] of Object.entries(model_dict)) {
                if (!key.startsWith('element_')) {
                    value.visible = false
                }
            }
        """,
    )
    hide_all_spectra.js_on_click(callback_hide_all_spectra)

    show_all_spectra = Button(
        name="Show All Spectra", label="Show All Spectra", width_policy="min"
    )
    callback_show_all_spectra = CustomJS(
        args={'model_dict': model_dict},
        code="""
            for (const[key, value] of Object.entries(model_dict)) {
                if (!key.startsWith('element_')) {
                    value.visible = true
                }
            }
        """,
    )
    show_all_spectra.js_on_click(callback_show_all_spectra)

    reset_checkboxes_button = Button(
        name="Reset Checkboxes", label="Reset Checkboxes", width_policy="min"
    )
    callback_reset_specs = CustomJS(
        args={
            'all_column_checkboxes': all_column_checkboxes,
        },
        code=f"""
            for (let i = 0; i < {len(all_column_checkboxes)}; i++) {{
                all_column_checkboxes[i].active = [];
            }}
        """,
    )
    reset_checkboxes_button.js_on_click(callback_reset_specs)

    # Move spectral lines when redshift or velocity changes
    speclines = {f'specline_{i}': line for i, line in enumerate(shifting_elements)}
    callback_zvs = CustomJS(
        args={'z': z_input, 'v_exp': v_exp_input, **speclines},
        code=f"""
                const c = 299792.458; // speed of light in km / s
                for (let i = 0; i < {len(speclines)}; i = i + 1) {{
                    let el = eval("specline_" + i);
                    el.data_source.data.x = el.data_source.data.wavelength.map(
                        x_i => ( x_i * (1 + z.value) /
                                        (1 + v_exp.value / c) )
                    );
                    el.data_source.change.emit();
                }}
            """,
    )

    # Hook up callback that shifts spectral lines when z or v changes
    z_input.js_on_change('value', callback_zvs)
    v_exp_input.js_on_change('value', callback_zvs)

    z_input.js_on_change(
        'value',
        CustomJS(
            args={'z': z_input, 'slider': z_slider},
            code="""
                    // Update slider value to match text input
                    slider.value = z.value;
                """,
        ),
    )

    v_exp_input.js_on_change(
        'value',
        CustomJS(
            args={'slider': v_exp_slider, 'v_exp': v_exp_input},
            code="""
                    // Update slider value to match text input
                    slider.value = v_exp.value;
                """,
        ),
    )

    on_top_spectra_dropdown = Dropdown(
        label="Select on top spectra",
        menu=[
            (legend_item.label['value'], str(legend_item.id))
            for legend_item in legend_items
        ],
        width_policy="min",
    )
    on_top_spectra_dropdown.js_on_event(
        "menu_item_click",
        CustomJS(
            args={'model_dict': model_dict, 'label_dict': label_dict},
            code="""
            for (const[key, value] of Object.entries(model_dict)) {
                if (!key.startsWith('element_') && (key.charAt(key.length - 1) === label_dict[this.item].toString())) {
                    value.level = 'glyph'
                }
                else {
                    value.level = 'underlay'
                }
            }
            """,
        ),
    )

    row1 = row(all_column_checkboxes)
    row2 = (
        column(
            on_top_spectra_dropdown,
            show_all_spectra,
            hide_all_spectra,
            reset_checkboxes_button,
        )
        if "mobile" in device
        else row(
            on_top_spectra_dropdown,
            show_all_spectra,
            hide_all_spectra,
            reset_checkboxes_button,
        )
    )
    row3 = (
        column(z, v_exp, smooth_column)
        if "mobile" in device
        else row(z, v_exp, smooth_column)
    )
    row4 = row(w)
    return column(
        plot,
        row1,
        row2,
        row3,
        row4,
        sizing_mode='stretch_width',
        width=width,
        height=plot_height,
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

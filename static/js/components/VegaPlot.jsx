import React from 'react';
import PropTypes from 'prop-types';
import embed from 'vega-embed';


const spec = (url) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  data: {
    url,
    format: {
      type: "json",
      property: "data" // where on the JSON does the data live
    }
  },
  background: "transparent",
  layer: [
    {
      selection: {
        filterMags: {
          type: "multi",
          fields: ["filter"],
          bind: "legend"
        },
        grid: {
          type: "interval",
          bind: "scales"
        }
      },
      mark: {
        type: "point",
        shape: "circle",
        filled: "true",
        size: 15,
      },
      transform: [
        { calculate: "join([format(datum.mag, '.2f'), ' ± ', format(datum.magerr, '.2f'), ' (', datum.magsys, ')'], '')", as: "magAndErr" }
      ],
      encoding: {
        x: {
          field: "mjd",
          type: "quantitative",
          scale: {
            zero: false,
          },
        },
        y: {
          field: "mag",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true
          },
          axis: {
            title: "mag"
          }
        },
        color: {
          field: "filter",
          type: "nominal",
          scale: { domain: ["ztfg", "ztfr", "ztfi"], range: ["#377E22", "#EA3323", "#CCCC52"] }
        },
        tooltip: [
          { field: "magAndErr", title: "mag", type: "nominal" },
          { field: "filter", type: "ordinal" },
          { field: "mjd", type: "quantitative" },
          { field: "limiting_mag", type: "quantitative", format: ".2f" }
        ],
        opacity: {
          condition: { selection: "filterMags", value: 1 },
          value: 0
        }
      }
    },

    // Render error bars
    {
      selection: {
        filterErrBars: {
          type: "multi",
          fields: ["filter"],
          bind: "legend"
        }
      },
      transform: [
        { filter: "datum.mag != null && datum.magerr != null" },
        { calculate: "datum.mag - datum.magerr", as: "magMin" },
        { calculate: "datum.mag + datum.magerr", as: "magMax" }
      ],
      mark: {
        type: "rule",
        size: 0.5
      },
      encoding: {
        x: {
          field: "mjd",
          type: "quantitative",
          scale: {
            zero: false,
          }
        },
        y: {
          field: "magMin",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true
          }
        },
        y2: {
          field: "magMax",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true
          }
        },
        color: {
          field: "filter",
          type: "nominal"
        },
        opacity: {
          condition: { selection: "filterErrBars", value: 1 },
          value: 0
        }
      }
    },

    // Render limiting mags
    {
      transform: [
        { filter: "datum.mag == null" }
      ],
      selection: {
        filterLimitingMags: {
          type: "multi",
          fields: ["filter"],
          bind: "legend"
        }
      },
      mark: {
        type: "point",
        shape: "triangle-down"
      },
      encoding: {
        x: {
          field: "mjd",
          type: "quantitative",
          scale: {
            zero: false,
          }
        },
        y: {
          field: "limiting_mag",
          type: "quantitative"
        },
        color: {
          field: "filter",
          type: "nominal"
        },
        opacity: {
          condition: { selection: "filterLimitingMags", value: 0.3 },
          value: 0
        }
      }
    }
  ]
});


const airmass_spec = (url) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  data: {
    url,
    format: {
      type: "json",
      property: "data" // where on the JSON does the data live
    }
  },
  background: "transparent",
  mark: "line",
  encoding: {
    x: { field: "time", type: "temporal", title: "time (UT)" },
    y: { field: "airmass", type: "quantitative", scale: { reverse: true } }
  }
});


class VegaPlot extends React.Component {
  // This is implemented as a class so we can define
  // shouldComponentUpdate

  shouldComponentUpdate() {
    // Don't re-render Vega plots if the containing div updates.
    // This dramatically improves browser performance

    return false;
  }

  render() {
    const { type, dataUrl } = this.props;

    const myspec = type === "light_curve" ? spec : airmass_spec;

    return (
      <div
        ref={
          (node) => {
            embed(node, myspec(dataUrl), {
              actions: false
            });
          }
        }
      />
    );
  }
}

VegaPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired,
  type: PropTypes.string
};

VegaPlot.defaultProps = {
  type: "light_curve"
};

export default VegaPlot;

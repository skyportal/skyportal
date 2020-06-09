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
  layer: [
    {
      mark: {
        type: "point",
        shape: "circle",
        filled: "true",
        size: 15
      },
      encoding: {
        x: {
          field: "mjd",
          type: "temporal"
        },
        y: {
          field: "mag",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true
          }
        },
        color: {
          field: "filter",
          type: "nominal"
        }
      }
    },
    //
    // // Render error bars
    // {
    //   transform: [
    //     {filter: "datum.mag != null && datum.magerr != null"},
    //     {calculate: "datum.mag - 0.1", "as": "magMin"},
    //     {calculate: "datum.mag + 0.1", "as": "magMax"},
    //   ],
    //   mark: {
    //     type: rule,
    //   },
    //   encoding: {
    //     x: {
    //       field: "mjd",
    //       type: "temporal"
    //     },
    //     y: {
    //       field: "magMin",
    //       type: "quantitative",
    //       scale: {
    //         zero: false,
    //         reverse: true
    //       }
    //     },
    //     y2: {
    //       field: "magMax",
    //       type: "quantitative",
    //       scale: {
    //         zero: false,
    //         reverse: true
    //       }
    //     },
    //     color: {
    //       field: "filter",
    //       type: "nominal"
    //     }
    //   }
    // },
    //
    // // Render limiting mags
    // {
    //   mark: {
    //     type: "point",
    //     shape: "triangle-down",
    //     opacity: 0.1
    //   },
    //   encoding: {
    //     x: {
    //       field: "mjd",
    //       type: "temporal"
    //     },
    //     y: {
    //       field: "limiting_mag",
    //       type: "quantitative",
    //     },
    //     color: {
    //       field: "filter",
    //       type: "nominal"
    //     }
    //   }
    // }
  ]
});


const VegaPlot = ({ dataUrl }) => (
  <div
    ref={
      (node) => {
        embed(node, spec(dataUrl), {
          actions: false
        });
      }
    }
  />
);

VegaPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired
};

export default VegaPlot;

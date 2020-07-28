import React from 'react';
import PropTypes from 'prop-types';
import embed from 'vega-embed';
import VegaPlot from './VegaPlot';


/*
const airmass_spec = (url, ephemeris) => ({
  $schema: "https://vega.github.io/schema/vega/v5.json",
  background: "transparent",
  width: 200,
  height: 200,
  data: {
    url: url,
    name: "airmass_api",
    format: {
      type: "json",
      property: "data" // where on the JSON does the data live
    }
  },
  scales: [
    {
      name: "xscale",
      type: "utc",
      domain: [ephemeris.sunset_utc, ephemeris.sunrise_utc],
      nice: "hour",
      range: "width",
      padding: 0.05
    },
    {
      name: "yscale",
      domain: [1, 4],
      reverse: true,
      range: "height",
    }
  ],
  axes: [
    {
      orient: "bottom",
      scale: "xscale",
      title: "Time (UT)"
    },
    {
      orient: "left",
      scale: "yscale",
      title: "Airmass"
    }
  ],
  marks: [
    {
      type: "line",
      clip: true,
      from: {
        data: "airmass_api"
      },
      encode: {
        enter: {
          x: {
            scale: "xscale",
            field: "time"
          },
          y: {
            scale: "yscale",
            field: "airmass"
          }
        }
      }
    }
  ]
});
*/
const airmass_spec = (url, ephemeris) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  background: "transparent",
  data: {
    url,
    format: {
      type: "json",
      property: "data" // where on the JSON does the data live
    }
  },
  layer:
    [
      {
        mark: {type: "line", clip: true},
        encoding: {
          x: {
            field: "time",
            type: "temporal",
            title: "time (UT)",
            scale: {
              domain: [
                ephemeris.twilight_evening_astronomical_utc,
                ephemeris.twilight_morning_astronomical_utc
              ]
            }
          },
          y: {
            field: "airmass",
            type: "quantitative",
            scale: {
              reverse: true,
              domain: [1, 4]
            }
          }
        }
      }
    ]
});



class AirmassPlot extends VegaPlot {

  render() {
    const { dataUrl, ephemeris } = this.props;
    return (
      <div
        ref={
          (node) => {
            embed(node, airmass_spec(dataUrl, ephemeris), {
              actions: false
            });
          }
        }
      />
    );
  }
}

AirmassPlot.propTypes = {
  ...VegaPlot.propTypes,
  ephemeris: PropTypes.object
};

export default AirmassPlot;

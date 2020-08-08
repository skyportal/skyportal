import React from 'react';
import PropTypes from 'prop-types';
import embed from 'vega-embed';
import VegaPlot from './VegaPlot';


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
        mark: { type: "line", clip: true },
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
  ephemeris: PropTypes.shape(
    {
      twilight_evening_astronomical_utc: PropTypes.number,
      twilight_morning_astronomical_utc: PropTypes.number,
      twilight_evening_nautical_utc: PropTypes.number,
      twilight_morning_nautical_utc: PropTypes.number,
      sunset_utc: PropTypes.number,
      sunrise_utc: PropTypes.number
    }
  ).isRequired
};

export default AirmassPlot;

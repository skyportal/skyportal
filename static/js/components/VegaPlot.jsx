import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { isMobileOnly } from "react-device-detect";
import PropTypes from "prop-types";
import embed from "vega-embed";
import * as photometryActions from "../ducks/photometry";
import * as filterActions from "../ducks/filter";
import wavelengthsToHex from "../wavelengthConverter";

const mjdNow = Date.now() / 86400000.0 + 40587.0;

const spec = (url, colorScale) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  data: {
    url,
    format: {
      type: "json",
      property: "data", // where on the JSON does the data live
    },
  },
  background: "transparent",
  layer: [
    {
      selection: {
        filterMags: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
        grid: {
          type: "interval",
          bind: "scales",
        },
      },
      mark: {
        type: "point",
        shape: "circle",
        filled: "true",
        size: 15,
      },
      transform: [
        {
          calculate:
            "join([format(datum.mag, '.2f'), ' ± ', format(datum.magerr, '.2f'), ' (', datum.magsys, ')'], '')",
          as: "magAndErr",
        },
        { calculate: `${mjdNow} - datum.mjd`, as: "daysAgo" },
      ],
      encoding: {
        x: {
          field: "daysAgo",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "days ago",
          },
        },
        y: {
          field: "mag",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "mag",
          },
        },
        color: {
          field: "filter",
          type: "nominal",
          scale: colorScale,
        },
        tooltip: [
          { field: "magAndErr", title: "mag", type: "nominal" },
          { field: "filter", type: "ordinal" },
          { field: "mjd", type: "quantitative" },
          { field: "daysAgo", type: "quantitative" },
          { field: "limiting_mag", type: "quantitative", format: ".2f" },
        ],
        opacity: {
          condition: { selection: "filterMags", value: 1 },
          value: 0,
        },
      },
    },

    // Render error bars
    {
      selection: {
        filterErrBars: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
      },
      transform: [
        { filter: "datum.mag != null && datum.magerr != null" },
        { calculate: "datum.mag - datum.magerr", as: "magMin" },
        { calculate: "datum.mag + datum.magerr", as: "magMax" },
        { calculate: `${mjdNow} - datum.mjd`, as: "daysAgo" },
      ],
      mark: {
        type: "rule",
        size: 0.5,
      },
      encoding: {
        x: {
          field: "daysAgo",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "days ago",
          },
        },
        y: {
          field: "magMin",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
        },
        y2: {
          field: "magMax",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
        },
        color: {
          field: "filter",
          type: "nominal",
          legend: {
            orient: isMobileOnly ? "bottom" : "right",
          },
        },
        opacity: {
          condition: { selection: "filterErrBars", value: 1 },
          value: 0,
        },
      },
    },

    // Render limiting mags
    {
      transform: [
        { filter: "datum.mag == null" },
        { calculate: `${mjdNow} - datum.mjd`, as: "daysAgo" },
      ],
      selection: {
        filterLimitingMags: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
      },
      mark: {
        type: "point",
        shape: "triangle-down",
      },
      encoding: {
        x: {
          field: "daysAgo",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            title: "days ago",
          },
        },
        y: {
          field: "limiting_mag",
          type: "quantitative",
        },
        color: {
          field: "filter",
          type: "nominal",
        },
        opacity: {
          condition: { selection: "filterLimitingMags", value: 0.3 },
          value: 0,
        },
      },
    },
  ],
});

const VegaPlot = React.memo((props) => {
  const { dataUrl, sourceId } = props;
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[sourceId]);

  useEffect(() => {
    if (!photometry) {
      dispatch(photometryActions.fetchSourcePhotometry(sourceId));
    }
  }, [sourceId, photometry, dispatch]);

  const filters = photometry
    ? [...new Set(photometry.map((datum) => datum.filter))]
    : null;
  const [wavelengths, setWavelengths] = useState([]);
  useEffect(() => {
    const getWavelengths = async () => {
      const result = await dispatch(
        filterActions.fetchFilterWavelengths(filters)
      );
      if (result.status === "success") {
        setWavelengths(wavelengthsToHex(result.data.wavelengths));
      }
    };
    if (filters) {
      getWavelengths();
    }
  }, [photometry]);
  const colorScale = {
    domain: filters,
    range: wavelengths,
  };
  return (
    <div
      ref={(node) => {
        if (node) {
          embed(node, spec(dataUrl, colorScale), {
            actions: false,
          });
        }
      }}
    />
  );
});

VegaPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired,
  sourceId: PropTypes.string.isRequired,
};

VegaPlot.displayName = "VegaPlot";

export default VegaPlot;

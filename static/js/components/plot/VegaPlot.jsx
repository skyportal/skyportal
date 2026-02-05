import React, { useEffect, useRef } from "react";
import { isMobileOnly } from "react-device-detect";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";

const mjdNow = Date.now() / 86400000.0 + 40587.0;

const spec = (
  url,
  colorScale,
  titleFontSize,
  labelFontSize,
  values,
  hasStyle,
  style,
) => {
  const hasValuesArray = Array.isArray(values);
  const hasDetections =
    !hasValuesArray ||
    values.some(
      (datum) => datum?.mag != null && Number.isFinite(Number(datum?.mjd)),
    );
  const hasLimitingMags =
    !hasValuesArray ||
    values.some(
      (datum) =>
        datum?.mag == null &&
        Number.isFinite(Number(datum?.limiting_mag)) &&
        Number.isFinite(Number(datum?.mjd)),
    );
  const layers = [];
  if (hasDetections) {
    layers.push({
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
        size: 24,
      },
      transform: [
        {
          calculate:
            "join([format(datum.mag, '.2f'), ' ± ', format(datum.magerr, '.2f'), ' (', datum.magsys, ')'], '')",
          as: "magAndErr",
        },
        { calculate: "toNumber(datum.mjd)", as: "mjdNum" },
        { filter: "isFinite(datum.mjdNum)" },
        { calculate: `${mjdNow} - datum.mjdNum`, as: "daysAgo" },
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
            titleFontSize,
            labelFontSize,
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
            titleFontSize,
            labelFontSize,
          },
        },
        color: {
          field: "filter",
          type: "nominal",
          scale: colorScale,
          legend: {
            titleAnchor: "start",
            offset: 5,
          },
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
    });
    layers.push({
      selection: {
        filterErrBars: {
          type: "multi",
          fields: ["filter"],
          bind: "legend",
        },
      },
      transform: [
        { filter: "datum.mag != null && datum.magerr != null" },
        { calculate: "toNumber(datum.mjd)", as: "mjdNum" },
        { filter: "isFinite(datum.mjdNum)" },
        { calculate: "datum.mag - datum.magerr", as: "magMin" },
        { calculate: "datum.mag + datum.magerr", as: "magMax" },
        { calculate: `${mjdNow} - datum.mjdNum`, as: "daysAgo" },
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
            padding: 0,
          },
          axis: {
            title: "days ago",
            titleFontSize,
            labelFontSize,
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
            titleFontSize,
            labelFontSize,
          },
        },
        opacity: {
          condition: { selection: "filterErrBars", value: 1 },
          value: 0,
        },
      },
    });
  }
  if (hasLimitingMags) {
    layers.push({
      transform: [
        { calculate: "toNumber(datum.limiting_mag)", as: "limitingMagNum" },
        {
          filter: "datum.mag == null && isFinite(datum.limitingMagNum)",
        },
        { calculate: "toNumber(datum.mjd)", as: "mjdNum" },
        { filter: "isFinite(datum.mjdNum)" },
        { calculate: `${mjdNow} - datum.mjdNum`, as: "daysAgo" },
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
            titleFontSize,
            labelFontSize,
          },
        },
        y: {
          field: "limitingMagNum",
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
    });
  }
  const specJSON = {
    $schema: "https://vega.github.io/schema/vega-lite/v6.2.0.json",
    background: "transparent",
    layer: layers,
  };
  if (url) {
    specJSON.data = {
      url,
      format: {
        type: "json",
        property: "data", // where on the JSON does the data live
      },
    };
  } else {
    specJSON.data = {
      values,
    };
  }
  if (hasStyle) {
    if (style.width || style.maxWidth || style.minWidth) {
      specJSON.layer[0].width = "container";
    }
    if (style.height || style.maxHeight || style.minHeight) {
      specJSON.layer[0].height = "container";
    }
    specJSON.layer[0].autosize = {
      type: "fit",
      contains: "padding",
    };
  }
  return specJSON;
};

const VegaPlot = React.memo((props) => {
  const { dataUrl, colorScale, values, style } = props;
  const hasStyle = Object.keys(style).length > 0;
  const theme = useTheme();
  const containerRef = useRef(null);
  const viewRef = useRef(null);

  useEffect(() => {
    // Flag to prevent memory leaks when the component unmounts before async render completes
    let cancelled = false;

    const renderPlot = async () => {
      if (!containerRef.current) {
        return;
      }

      // Finalize any previous Vega view to clean up its event listeners, scales, and DOM resources.
      // This is critical: Vega views hold references to DOM nodes and register event handlers.
      // Without calling finalize(), these resources persist and cause memory growth in virtualized lists.
      if (viewRef.current) {
        viewRef.current.finalize();
        viewRef.current = null;
      }

      // Embed the new Vega visualization. This is async because it may fetch data.
      const result = await embed(
        containerRef.current,
        spec(
          dataUrl,
          colorScale,
          theme.plotFontSizes.titleFontSize,
          theme.plotFontSizes.labelFontSize,
          values,
          hasStyle,
          style,
        ),
        {
          actions: false,
        },
      );

      // If the component was unmounted or dependencies changed while we were rendering,
      // immediately finalize the newly created view to avoid leaking it.
      if (cancelled) {
        result?.view?.finalize();
        return;
      }

      // Store the view reference for cleanup on next render or unmount.
      viewRef.current = result?.view || null;
    };

    renderPlot();

    // Cleanup function: runs when dependencies change or component unmounts.
    // This ensures Vega views are properly disposed, preventing memory leaks.
    return () => {
      cancelled = true;
      if (viewRef.current) {
        viewRef.current.finalize();
        viewRef.current = null;
      }
      // Clear the DOM container to help garbage collection.
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [
    dataUrl,
    colorScale,
    values,
    hasStyle,
    style,
    theme.plotFontSizes.titleFontSize,
    theme.plotFontSizes.labelFontSize,
  ]);

  return <div style={style || {}} ref={containerRef} />;
});

VegaPlot.propTypes = {
  dataUrl: PropTypes.string,
  colorScale: PropTypes.shape({
    domain: PropTypes.arrayOf(PropTypes.string),
    range: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  values: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/forbid-prop-types
  style: PropTypes.shape({}),
};

VegaPlot.defaultProps = {
  dataUrl: null,
  values: null,
  style: {},
};

VegaPlot.displayName = "VegaPlot";

export default VegaPlot;

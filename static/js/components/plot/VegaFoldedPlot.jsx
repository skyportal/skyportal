import React, { useEffect, useRef } from "react";
import { isMobileOnly } from "react-device-detect";
import PropTypes from "prop-types";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";

const spec = (url, colorScale, titleFontSize, labelFontSize, values) => {
  const specJSON = {
    $schema: "https://vega.github.io/schema/vega-lite/v6.2.0.json",
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
        ],
        encoding: {
          x: {
            field: "phase",
            type: "quantitative",
            scale: {
              zero: false,
              reverse: false,
            },
            axis: {
              title: "Phase",
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
              titleFontSize,
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
          },
          tooltip: [
            { field: "magAndErr", title: "mag", type: "nominal" },
            { field: "filter", type: "ordinal" },
            { field: "mjd", type: "quantitative" },
            { field: "phase", type: "quantitative" },
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
        ],
        mark: {
          type: "rule",
          size: 0.5,
        },
        encoding: {
          x: {
            field: "phase",
            type: "quantitative",
            scale: {
              zero: false,
              reverse: false,
            },
            axis: {
              title: "Phase",
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
      },

      // Render limiting mags
      {
        transform: [{ filter: "datum.mag == null" }],
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
            field: "phase",
            type: "quantitative",
            scale: {
              zero: false,
              reverse: false,
            },
            axis: {
              title: "Phase",
              titleFontSize,
              labelFontSize,
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
  return specJSON;
};

const VegaFoldedPlot = React.memo((props) => {
  const { dataUrl, colorScale, values } = props;
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
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [
    dataUrl,
    colorScale,
    values,
    theme.plotFontSizes.titleFontSize,
    theme.plotFontSizes.labelFontSize,
  ]);

  return <div ref={containerRef} />;
});

VegaFoldedPlot.propTypes = {
  dataUrl: PropTypes.string,
  colorScale: PropTypes.shape({
    domain: PropTypes.arrayOf(PropTypes.string),
    range: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  values: PropTypes.arrayOf(PropTypes.object), // eslint-disable-line react/forbid-prop-types
};

VegaFoldedPlot.defaultProps = {
  dataUrl: null,
  values: null,
};

VegaFoldedPlot.displayName = "VegaFoldedPlot";

export default VegaFoldedPlot;

import embed from "vega-embed";

// Consistent color palette for photometric bands across surveys
const BAND_COLOR_SCALE = {
  domain: ["u", "g", "r", "i", "z", "y"],
  range: ["#7B2D8B", "#28a745", "#dc3545", "#f3dc11", "#ff8c00", "#8B4513"],
};

const spec = (url: any, values: any, jd: any): any => {
  const specJSON: any = {
    $schema: "https://vega.github.io/schema/vega-lite/v5.2.0.json",
    width: "container",
    height: "container",
    autosize: {
      type: "fit",
      resize: true,
    },
    background: "transparent",
    layer: [
      // Render error bars
      {
        selection: {
          filterErrBars: {
            type: "multi",
            fields: ["band"],
            bind: "legend",
          },
        },
        transform: [
          { filter: "datum.magpsf != null && datum.sigmapsf != null" },
          { calculate: "datum.magpsf - datum.sigmapsf", as: "magMin" },
          { calculate: "datum.magpsf + datum.sigmapsf", as: "magMax" },
        ],
        mark: {
          type: "rule",
          size: 2,
        },
        encoding: {
          x: {
            field: "jd",
            type: "quantitative",
            scale: { zero: false },
          },
          y: {
            field: "magMin",
            type: "quantitative",
            scale: { zero: false, reverse: true },
          },
          y2: {
            field: "magMax",
            type: "quantitative",
          },
          color: {
            field: "band",
            type: "nominal",
            scale: BAND_COLOR_SCALE,
          },
          opacity: {
            condition: { selection: "filterErrBars", value: 1 },
            value: 0,
          },
        },
      },

      // Render detections
      {
        selection: {
          filterMags: {
            type: "multi",
            fields: ["band"],
            bind: "legend",
          },
          grid: {
            name: "grid",
            type: "interval",
            bind: "scales",
          },
        },
        mark: {
          type: "point",
          shape: "circle",
          filled: true,
          size: 100,
        },
        transform: [
          {
            calculate:
              "join([format(datum.magpsf, '.2f'), ' ± ', format(datum.sigmapsf, '.2f'), ' (ab)'], '')",
            as: "magAndErr",
          },
        ],
        encoding: {
          x: {
            field: "jd",
            type: "quantitative",
            scale: { zero: false },
          },
          y: {
            field: "magpsf",
            type: "quantitative",
            scale: { zero: false, reverse: true },
            axis: { title: "mag" },
          },
          color: {
            field: "band",
            type: "nominal",
            scale: BAND_COLOR_SCALE,
          },
          tooltip: [
            { field: "magAndErr", title: "mag", type: "nominal" },
            { field: "band", type: "nominal" },
            { field: "jd", type: "quantitative" },
            { field: "diffmaglim", type: "quantitative", format: ".2f" },
            { field: "origin", type: "ordinal" },
          ],
          opacity: {
            condition: { selection: "filterMags", value: 1 },
            value: 0,
          },
        },
      },

      // Render limiting mags (non-detections)
      {
        transform: [{ filter: "datum.magpsf == null" }],
        selection: {
          filterLimitingMags: {
            type: "multi",
            fields: ["band"],
            bind: "legend",
          },
        },
        mark: {
          type: "point",
          shape: "triangle-down",
          size: 60,
        },
        encoding: {
          x: {
            field: "jd",
            type: "quantitative",
            scale: { zero: false },
          },
          y: {
            field: "diffmaglim",
            type: "quantitative",
          },
          color: {
            field: "band",
            type: "nominal",
            scale: BAND_COLOR_SCALE,
          },
          tooltip: [
            { field: "band", type: "nominal" },
            { field: "jd", type: "quantitative" },
            { field: "diffmaglim", type: "quantitative", format: ".2f" },
          ],
          opacity: {
            condition: { selection: "filterLimitingMags", value: 0.3 },
            value: 0,
          },
        },
      },

      // Vertical rule marking the selected alert's JD
      {
        data: { values: [{}] },
        mark: { type: "rule", strokeDash: [4, 4], size: 1, opacity: 0.3 },
        encoding: {
          x: {
            datum: jd,
            type: "quantitative",
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
        property: "data.prv_candidates",
      },
    };
  } else {
    specJSON.data = { values };
  }
  return specJSON;
};

interface VegaPlotProps {
  dataUrl?: any;
  values?: any;
  jd: number;
}

const VegaPlot = ({ dataUrl = null, values = null, jd }: VegaPlotProps) => {
  if (!dataUrl && !values) {
    return null;
  }
  return (
    <div
      ref={(node) => {
        embed(node as any, spec(dataUrl, values, jd), {
          actions: false,
        });
      }}
      style={{ width: "100%", height: "100%" }}
    />
  );
};

export default VegaPlot;

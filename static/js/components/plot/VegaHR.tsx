import React from "react";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";

const rootURL = `${window.location.protocol}//${window.location.host}`;

const spec = (
  data: any,
  textColor: string,
  width = 200,
  height = 200,
  titleFontSize?: number,
  labelFontSize?: number,
): any => ({
  $schema: "https://vega.github.io/schema/vega-lite/v6.2.0.json",
  width,
  height,
  padding: 0.025 * Math.min(width, height),
  background: "transparent",
  layer: [
    // draw the Gaia data for main sequence etc.
    {
      data: {
        url: `${rootURL}/static/HR_density.json`,
        format: {
          type: "json",
        },
        //         property: "data",
      },
      background: "transparent",
      encoding: {
        x: {
          field: "color",
          type: "quantitative",
          axis: {
            title: "Bp-Rp",
            grid: false,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
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
            title: "Absolute Magnitude G",
            grid: false,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
            titleFontSize,
            labelFontSize,
          },
        },
        color: {
          name: "count",
          field: "count",
          type: "quantitative",
          legend: null,
        },
      },
      mark: {
        type: "point",
        shape: "circle",
        size: 2,
        filled: "true",
        from: { data: "count" },
        update: {
          fill: { scale: "color", field: "count" },
        },
        tooltip: true,
      },
    },

    // make the point for the current object
    {
      data: { values: data },
      selection: {
        filterPoints: {
          type: "multi",
          fields: ["origin"],
          bind: "legend",
        },
      },
      encoding: {
        x: {
          field: "color",
          type: "quantitative",
          axis: {
            title: "Bp-Rp",
            grid: false,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
            titleFontSize,
            labelFontSize,
          },
        },
        y: {
          field: "abs_mag",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            grid: false,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
            titleFontSize,
            labelFontSize,
          },
        },
        color: {
          field: "origin",
          type: "nominal",
          legend: {
            orient: "bottom",
            labelColor: textColor,
            titleColor: textColor,
            titleFontSize,
            labelFontSize,
          },
        },
        opacity: {
          condition: { selection: "filterPoints", value: 1 },
          value: 0.2,
        },
      },
      mark: {
        type: "point",
        shape: "circle",
        size: 50,
        filled: true,
        tooltip: true,
      },
    },

    // make the cross around the point
    {
      data: { values: data },
      selection: {
        filterCrosses: {
          type: "multi",
          fields: ["origin"],
          bind: "legend",
        },
      },
      encoding: {
        x: {
          field: "color",
          type: "quantitative",
          axis: {
            title: "Bp-Rp",
            grid: false,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
            titleFontSize,
            labelFontSize,
          },
        },
        y: {
          field: "abs_mag",
          type: "quantitative",
          scale: {
            zero: false,
            reverse: true,
          },
          axis: {
            grid: false,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
            titleFontSize,
            labelFontSize,
          },
        },
        color: {
          field: "origin",
          type: "nominal",
          legend: null,
        },
        opacity: {
          condition: { selection: "filterCrosses", value: 1 },
          value: 0.2,
        },
      },
      mark: {
        type: "point",
        shape: "cross",
        size: 300,
        angle: 45,
        filled: false,
        tooltip: true,
      },
    },
  ],
});

interface VegaHRProps {
  data: {
    abs_mag: number;
    color: number;
    origin: string;
  }[];
  width?: number;
  height?: number;
}

const VegaHR = React.memo((props: VegaHRProps) => {
  const { data, width = 200, height = 200 } = props;
  const theme = useTheme() as any;

  return (
    <div
      ref={(node) => {
        if (node) {
          embed(
            node,
            spec(
              data,
              theme.palette.text.primary,
              width,
              height,
              theme.plotFontSizes.titleFontSize,
              theme.plotFontSizes.labelFontSize,
            ),
            {
              actions: false,
            },
          );
        }
      }}
    />
  );
});

VegaHR.displayName = "VegaHR";

export default VegaHR;

import { useMemo, useState } from "react";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { OutburstPoint, outburstReport } from "./outburstTransforms";

const Plot = createPlotlyComponent(Plotly);

// Per-band marker colours, matching the ZBrowser convention.
const BAND_COLORS: Record<string, string> = {
  u: "#1f77b4",
  g: "#2ca02c",
  r: "#ff7f0e",
  i: "#d62728",
  z: "#e377c2",
  y: "#9467bd",
};

// Outburst threshold (sigma) above which the test point is flagged.
const OUTBURST_THRESHOLD = 3;

type YMode = "m" | "H" | "Hcolor";

const Y_MODES: { key: YMode; label: string; axis: string }[] = [
  { key: "m", label: "Apparent m", axis: "m (mag)" },
  { key: "H", label: "H(1,1,0)", axis: "H(1,1,0) (mag)" },
  { key: "Hcolor", label: "H − colour", axis: "H(1,1,0) − C (mag)" },
];

interface OutburstPlotProps {
  points: OutburstPoint[];
}

const OutburstPlot = ({ points }: OutburstPlotProps) => {
  const [yMode, setYMode] = useState<YMode>("H");
  const report = useMemo(() => outburstReport(points), [points]);

  if (!report) {
    return (
      <Typography sx={{ p: 2 }}>
        Not enough solar-system photometry with geometry in the window to
        compute an outburst statistic.
      </Typography>
    );
  }

  const yValues =
    yMode === "m" ? report.m : yMode === "H" ? report.H : report.Hcolor;
  const yAxisTitle = Y_MODES.find((mode) => mode.key === yMode)!.axis;

  const bandsPresent = Array.from(new Set(report.bands));
  const lcTraces = bandsPresent.map((band) => {
    const idx = report.bands
      .map((b, k) => (b === band ? k : -1))
      .filter((k) => k >= 0);
    return {
      x: idx.map((k) => report.dt[k]),
      y: idx.map((k) => yValues[k]),
      error_y: {
        type: "data" as const,
        array: idx.map((k) => report.unc[k]),
        visible: true,
      },
      mode: "markers" as const,
      type: "scatter" as const,
      name: band,
      marker: { color: BAND_COLORS[band] || "#888", size: 7 },
    };
  });

  // Dashed line at the tested value (colour-removed panel only, like the figure).
  const shapes =
    yMode === "Hcolor"
      ? [
          {
            type: "line" as const,
            xref: "paper" as const,
            x0: 0,
            x1: 1,
            y0: report.testValue,
            y1: report.testValue,
            line: { dash: "dash" as const, color: "#000", width: 1 },
          },
        ]
      : [];

  const lcLayout = {
    autosize: true,
    height: 340,
    margin: { l: 60, r: 15, t: 10, b: 45 },
    xaxis: { title: "dt (days)" },
    yaxis: { title: yAxisTitle, autorange: "reversed" as const },
    shapes,
    legend: { orientation: "h" as const },
    showlegend: true,
  };

  const histLayout = {
    autosize: true,
    height: 200,
    margin: { l: 50, r: 15, t: 10, b: 45 },
    xaxis: { title: "O (σ from trend)" },
    yaxis: { title: "Count" },
    shapes: [
      {
        type: "line" as const,
        yref: "paper" as const,
        x0: report.medianO,
        x1: report.medianO,
        y0: 0,
        y1: 1,
        line: { color: "#000", width: 2 },
      },
    ],
  };

  const isOutburst = report.medianO > OUTBURST_THRESHOLD;

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          flexWrap: "wrap",
          mb: 1,
        }}
      >
        <ToggleButtonGroup
          size="small"
          exclusive
          value={yMode}
          onChange={(_e, v) => v && setYMode(v)}
        >
          {Y_MODES.map((mode) => (
            <ToggleButton key={mode.key} value={mode.key}>
              {mode.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <Tooltip
          title={`Median of the per-point outburst statistics over ${report.nPoints} points (threshold ${OUTBURST_THRESHOLD}σ)`}
        >
          <Chip
            label={`median O = ${report.medianO.toFixed(2)}${
              isOutburst ? " — outburst" : ""
            }`}
            color={isOutburst ? "error" : "success"}
            size="small"
          />
        </Tooltip>
      </Box>
      <Plot
        data={lcTraces as any}
        layout={lcLayout as any}
        config={{ displaylogo: false, responsive: true } as any}
        useResizeHandler
        style={{ width: "100%" }}
      />
      <Plot
        data={
          [
            {
              x: report.ostats,
              type: "histogram",
              marker: { color: "#1f77b4" },
            },
          ] as any
        }
        layout={histLayout as any}
        config={{ displaylogo: false, responsive: true } as any}
        useResizeHandler
        style={{ width: "100%" }}
      />
    </Box>
  );
};

export default OutburstPlot;

import { useMemo, useState } from "react";
import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import {
  fitBandColors,
  histogram,
  SsoPoint,
  outburstReport,
  reduceToUnitGeometry,
} from "./ssoTransforms";

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

// Outburst threshold (sigma) above which the most recent point is flagged.
const OUTBURST_THRESHOLD = 3;

// The inert-body heliocentric slope: reflected sunlight goes as rh^-2.
const INERT_SLOPE = -2;

type XKey = "mjd" | "phase" | "rh" | "delta" | "dt";
type YKey = "m" | "H_alpha" | "H";

const X_AXES: { key: XKey; label: string; title: string }[] = [
  { key: "mjd", label: "Modified Julian date", title: "MJD (days)" },
  { key: "dt", label: "Days from latest", title: "dt (days)" },
  { key: "phase", label: "Phase angle", title: "Phase angle (deg)" },
  { key: "rh", label: "Heliocentric distance", title: "rh (au)" },
  { key: "delta", label: "Geocentric distance", title: "Delta (au)" },
];

const Y_AXES: { key: YKey; label: string; title: string }[] = [
  { key: "m", label: "Apparent magnitude", title: "m (mag)" },
  {
    key: "H_alpha",
    label: "Reduced, phase kept",
    title: "H(1,1,α) (mag)",
  },
  { key: "H", label: "Reduced, phase removed", title: "H(1,1,0) (mag)" },
];

/** Light curve of a solar system object; the reduced views are the informative ones. */
export const useSolarSystemPlot = (points: SsoPoint[]) => {
  const [xKey, setXKey] = useState<XKey>("mjd");
  const [yKey, setYKey] = useState<YKey>("H");
  const [slopeText, setSlopeText] = useState(String(INERT_SLOPE));
  const [removeColor, setRemoveColor] = useState(true);
  const [showMasked, setShowMasked] = useState(true);

  // Empty or half-typed input falls back to the inert slope; commas are decimals.
  const typed = Number(slopeText.trim().replace(",", "."));
  const rhSlope =
    slopeText.trim() !== "" && Number.isFinite(typed) ? typed : INERT_SLOPE;

  const report = useMemo(() => outburstReport(points), [points]);
  const oHist = useMemo(
    () => (report ? histogram(report.ostats) : null),
    [report],
  );
  const colorFit = useMemo(
    () => fitBandColors(points, { rhSlope }),
    [points, rhSlope],
  );

  const series = useMemo(() => {
    if (points.length === 0) return null;
    const sorted = [...points].sort((a, b) => a.time - b.time);
    const tLast = sorted[sorted.length - 1]!.time;
    const mag = sorted.map((p) => p.mag);
    const rh = sorted.map((p) => p.rh);
    const delta = sorted.map((p) => p.delta);
    const phase = sorted.map((p) => p.phase);

    const y =
      yKey === "m"
        ? mag
        : reduceToUnitGeometry(mag, rh, delta, phase, {
            rhSlope,
            removePhase: yKey === "H",
          });
    // Putting each band on the reference band's scale is what makes a long curve legible.
    const shifted =
      removeColor && colorFit
        ? y.map((v, k) => v - (colorFit.colors[sorted[k]!.band]?.offset ?? 0))
        : y;

    const x = {
      mjd: sorted.map((p) => p.time),
      dt: sorted.map((p) => p.time - tLast),
      phase,
      rh,
      delta,
    }[xKey];

    return { sorted, x, y: shifted };
  }, [points, xKey, yKey, rhSlope, removeColor, colorFit]);

  const maskedCount = points.filter((p) => p.rejected).length;
  const isOutburst = (report?.medianO ?? 0) > OUTBURST_THRESHOLD;

  // Nights are quoted with the value: a colour from one night is barely a measurement.
  const colorSummary = colorFit
    ? Object.entries(colorFit.colors)
        .filter(([band]) => band !== colorFit.reference)
        .map(([band, fit]) => {
          const unc = !Number.isFinite(fit.uncertainty)
            ? ""
            : fit.uncertainty < 0.005
              ? " ± <0.01"
              : ` ± ${fit.uncertainty.toFixed(2)}`;
          const nights = `${fit.nights} night${fit.nights === 1 ? "" : "s"}`;
          return `${band}−${colorFit.reference} = ${fit.offset.toFixed(2)}${unc} mag from ${nights}`;
        })
        .join(", ")
    : "";

  return {
    xKey,
    setXKey,
    yKey,
    setYKey,
    slopeText,
    setSlopeText,
    removeColor,
    setRemoveColor,
    showMasked,
    setShowMasked,
    rhSlope,
    report,
    oHist,
    colorFit,
    series,
    maskedCount,
    isOutburst,
    colorSummary,
  };
};

export type SolarSystemPlotState = ReturnType<typeof useSolarSystemPlot>;

const labelledRow = { display: "flex", gap: "0.25rem", alignItems: "center" };

/** The tab's toggles, rendered into the shared photometry control block. */
export const SolarSystemControls = ({
  ctrl,
  gridItemClass,
}: {
  ctrl: SolarSystemPlotState;
  gridItemClass: string;
}) => {
  if (!ctrl.series) return null;
  return (
    <>
      <div className={gridItemClass}>
        <div style={labelledRow}>
          <Typography noWrap>X axis</Typography>
          <Select
            value={ctrl.xKey}
            onChange={(e) => ctrl.setXKey(e.target.value as XKey)}
            size="small"
            style={{ width: "12rem" }}
          >
            {X_AXES.map((axis) => (
              <MenuItem key={axis.key} value={axis.key}>
                {axis.label}
              </MenuItem>
            ))}
          </Select>
        </div>
        <div style={labelledRow}>
          <Typography noWrap>Y axis</Typography>
          <Select
            value={ctrl.yKey}
            onChange={(e) => ctrl.setYKey(e.target.value as YKey)}
            size="small"
            style={{ width: "12rem" }}
          >
            {Y_AXES.map((axis) => (
              <MenuItem key={axis.key} value={axis.key}>
                {axis.label}
              </MenuItem>
            ))}
          </Select>
        </div>
      </div>

      <div className={gridItemClass}>
        <div style={labelledRow}>
          <Tooltip title="Heliocentric exponent of the flux. -2 is reflected sunlight off an inert body; an active comet is steeper.">
            <Typography noWrap>Activity slope</Typography>
          </Tooltip>
          <TextField
            size="small"
            value={ctrl.slopeText}
            disabled={ctrl.yKey === "m"}
            onChange={(e) => ctrl.setSlopeText(e.target.value)}
            slotProps={{ htmlInput: { inputMode: "decimal" } }}
            style={{ width: "6rem" }}
          />
        </div>
        <div style={labelledRow}>
          <Typography noWrap>Remove colour</Typography>
          <Tooltip title="Shift each band onto the reference band using the fitted colours">
            <span>
              <Switch
                checked={ctrl.removeColor}
                disabled={!ctrl.colorFit}
                onChange={(e) => ctrl.setRemoveColor(e.target.checked)}
                size="small"
              />
            </span>
          </Tooltip>
        </div>
      </div>

      <div className={gridItemClass}>
        {ctrl.maskedCount > 0 && (
          <div style={labelledRow}>
            <Typography
              noWrap
            >{`Show ${ctrl.maskedCount} rejected`}</Typography>
            <Tooltip title="Rejected points are never fitted; this only draws them">
              <Switch
                checked={ctrl.showMasked}
                onChange={(e) => ctrl.setShowMasked(e.target.checked)}
                size="small"
              />
            </Tooltip>
          </div>
        )}
        {ctrl.report && (
          <div style={labelledRow}>
            <Tooltip
              title={`Median of the per-point outburst statistics over the trailing window (${ctrl.report.nPoints} points, threshold ${OUTBURST_THRESHOLD} sigma)`}
            >
              <Chip
                label={`median O = ${ctrl.report.medianO.toFixed(2)}${
                  ctrl.isOutburst ? " — outburst" : ""
                }`}
                color={ctrl.isOutburst ? "error" : "success"}
                size="small"
              />
            </Tooltip>
          </div>
        )}
      </div>
    </>
  );
};

const SolarSystemPlot = ({ ctrl }: { ctrl: SolarSystemPlotState }) => {
  const {
    series,
    colorFit,
    colorSummary,
    removeColor,
    showMasked,
    report,
    oHist,
    rhSlope,
    xKey,
    yKey,
  } = ctrl;

  if (!series) {
    return (
      <Typography sx={{ p: 2 }}>
        No solar-system photometry with per-point geometry yet. The heliocentric
        and geocentric distances and the phase angle arrive with the alert, so
        this fills in as those are ingested.
      </Typography>
    );
  }

  const { sorted, x, y } = series;
  const bands = Array.from(new Set(sorted.map((p) => p.band)));

  // "g-0.51" rather than "g", so the legend says what was subtracted.
  const bandLabel = (band: string) => {
    const offset = removeColor ? colorFit?.colors[band]?.offset : undefined;
    if (!offset) return band;
    return `${band}${offset > 0 ? "-" : "+"}${Math.abs(offset).toFixed(2)}`;
  };
  const traceFor = (band: string, masked: boolean) => {
    const idx = sorted
      .map((p, k) => (p.band === band && !!p.rejected === masked ? k : -1))
      .filter((k) => k >= 0);
    if (idx.length === 0) return null;
    return {
      x: idx.map((k) => x[k]),
      y: idx.map((k) => y[k]),
      error_y: {
        type: "data" as const,
        array: idx.map((k) => sorted[k]!.magerr),
        visible: true,
      },
      mode: "markers" as const,
      type: "scatter" as const,
      name: masked ? `${band} (rejected)` : bandLabel(band),
      // Rejected points stay as crosses; a gap would read as the object unobserved.
      marker: {
        color: BAND_COLORS[band] || "#888",
        size: masked ? 8 : 6,
        symbol: masked ? ("x" as const) : ("circle" as const),
        opacity: masked ? 0.45 : 1,
      },
      hovertemplate:
        `%{x:.4f}, %{y:.3f}<br>rh %{customdata[0]:.3f} au` +
        `, Δ %{customdata[1]:.3f} au, α %{customdata[2]:.2f}°` +
        "<extra>%{fullData.name}</extra>",
      customdata: idx.map((k) => [
        sorted[k]!.rh,
        sorted[k]!.delta,
        sorted[k]!.phase,
      ]),
    };
  };

  const traces = [
    ...bands.map((band) => traceFor(band, false)),
    ...(showMasked ? bands.map((band) => traceFor(band, true)) : []),
  ].filter(Boolean);

  const layout = {
    autosize: true,
    height: 420,
    margin: { l: 75, r: 15, t: 10, b: 110 },
    // Plotly 4 takes `title: { text }`; a bare string renders no label at all.
    xaxis: { title: { text: X_AXES.find((a) => a.key === xKey)!.title } },
    yaxis: {
      title: { text: Y_AXES.find((a) => a.key === yKey)!.title },
      autorange: "reversed" as const,
    },
    legend: {
      orientation: "h" as const,
      x: 0,
      y: -0.3,
      yanchor: "top" as const,
    },
    showlegend: true,
  };

  return (
    <Box>
      {colorFit && colorSummary && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", px: 2 }}
        >
          {colorSummary}
        </Typography>
      )}
      {yKey !== "m" && rhSlope !== INERT_SLOPE && (
        <Typography variant="caption" color="text.secondary" sx={{ px: 2 }}>
          Reduced with rh^{rhSlope} rather than the inert-body rh^{INERT_SLOPE},
          so these are activity-corrected magnitudes.
        </Typography>
      )}
      <Plot
        data={traces as any}
        layout={layout as any}
        config={{ displaylogo: false, responsive: true } as any}
        useResizeHandler
        style={{ width: "100%" }}
      />
      {report && (
        <Plot
          data={
            [
              {
                x: oHist!.centers,
                y: oHist!.counts,
                width: oHist!.width,
                type: "bar",
                marker: { color: "#1f77b4" },
              },
            ] as any
          }
          layout={
            {
              autosize: true,
              height: 200,
              margin: { l: 58, r: 15, t: 10, b: 52 },
              xaxis: { title: { text: "O (σ from trend)" } },
              yaxis: { title: { text: "Count" } },
              shapes: [
                {
                  type: "line",
                  yref: "paper",
                  x0: report.medianO,
                  x1: report.medianO,
                  y0: 0,
                  y1: 1,
                  line: { color: "#000", width: 2 },
                },
              ],
            } as any
          }
          config={{ displaylogo: false, responsive: true } as any}
          useResizeHandler
          style={{ width: "100%" }}
        />
      )}
    </Box>
  );
};

export default SolarSystemPlot;

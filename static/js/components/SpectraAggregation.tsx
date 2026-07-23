import { useMemo, useState } from "react";

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Slider from "@mui/material/Slider";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "./plot/plotlyScatter3d";
import {
  useGetBulkSpectraQuery,
  type BulkSpectraArgs,
  type BulkSpectraSource,
} from "../ducks/spectra";
import type { PhotStatPoint } from "../ducks/photStatAggregate";
import { smoothing_func } from "../utils";

const Plot = createPlotlyComponent(Plotly);

// Draw at most this many spectra; over it we downsample across phase (the server
// bounds how many sources/spectra it returns).
const MAX_SPECTRA = 200;
const MAX_SOURCES = 300;

type T0Mode = "first" | "peak" | "tns";
type Display = "waterfall" | "color";

// MJD from an ISO-ish datetime string (Unix epoch = MJD 40587).
const dateToMjd = (s?: string | null): number | null => {
  if (!s) return null;
  const ms = Date.parse(s.replace(" ", "T"));
  return Number.isNaN(ms) ? null : ms / 86400000 + 40587;
};

const median = (arr: number[]): number | null => {
  const v = arr.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = Math.floor(v.length / 2);
  if (v.length % 2) return v[m] as number;
  return ((v[m - 1] as number) + (v[m] as number)) / 2;
};

// p-th percentile (0-100) of the finite values (nearest-rank).
const percentile = (arr: number[], p: number): number | null => {
  const v = arr.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const idx = Math.min(
    v.length - 1,
    Math.max(0, Math.round((p / 100) * (v.length - 1))),
  );
  return v[idx] as number;
};

// Blue -> green -> red ramp for phase in [0, 1] (early -> late).
const phaseColor = (t: number): string => {
  const c = Math.max(0, Math.min(1, t));
  const r = Math.round(255 * Math.min(1, 1.5 * c));
  const g = Math.round(255 * Math.max(0, 1 - Math.abs(c - 0.5) * 2));
  const b = Math.round(255 * Math.min(1, 1.5 * (1 - c)));
  return `rgb(${r},${g},${b})`;
};

const t0For = (s: BulkSpectraSource, mode: T0Mode): number | null => {
  if (mode === "first") return s.first_detected_mjd ?? null;
  if (mode === "peak") return s.peak_mjd ?? null;
  return dateToMjd(s.tns_discovery_date);
};

const t0Label: Record<T0Mode, string> = {
  first: "first-detection MJD",
  peak: "peak MJD",
  tns: "TNS date",
};

interface SpectrumRecord {
  sourceId: string;
  phase: number;
  wl: number[];
  flux: number[];
}

const SpectraAggregation = ({ points }: { points: PhotStatPoint[] }) => {
  const [t0Mode, setT0Mode] = useState<T0Mode>("first");
  const [display, setDisplay] = useState<Display>("waterfall");
  const [restFrame, setRestFrame] = useState(true);
  const [normalize, setNormalize] = useState(true);
  // Percent trimmed off each tail when clipping (0 = off). 1% kills the
  // cosmic-ray/sky spikes seen in real data while barely touching normal spectra.
  const [clipPct, setClipPct] = useState(1);
  const [smoothWindow, setSmoothWindow] = useState(0);
  const [offsetMult, setOffsetMult] = useState(1);
  const [wlMin, setWlMin] = useState("");
  const [wlMax, setWlMax] = useState("");

  // Spectra follow the page's source selection (chosen at the top); one bulk
  // request fetches all their spectra. Null (skips the query) if nothing plotted.
  const bulkArgs: BulkSpectraArgs | null = useMemo(() => {
    const ids = points.map((p) => p.id);
    return ids.length ? { obj_ids: ids, maxSources: MAX_SOURCES } : null;
  }, [points]);

  const { data, isFetching } = useGetBulkSpectraQuery(
    bulkArgs as BulkSpectraArgs,
    { skip: !bulkArgs },
  );

  const meta = useMemo(() => {
    const m: Record<string, BulkSpectraSource> = {};
    (data?.sources ?? []).forEach((s) => {
      m[s.id] = s;
    });
    return m;
  }, [data]);

  // One record per spectrum, phase-sorted, with rest-frame / normalization
  // applied. Spectra whose source lacks the chosen t0 are dropped.
  const records = useMemo(() => {
    const recs: SpectrumRecord[] = [];
    (data?.spectra ?? []).forEach((sp) => {
      const src = meta[sp.obj_id];
      if (!src) return;
      const t0 = t0For(src, t0Mode);
      if (t0 == null) return;
      const wlRaw = sp.wavelengths;
      const flRaw = sp.fluxes;
      if (!Array.isArray(wlRaw) || !Array.isArray(flRaw) || !wlRaw.length)
        return;
      const mjd = dateToMjd(sp.observed_at);
      if (mjd == null) return;
      const z = src.redshift ?? null;
      const useRest = restFrame && z != null && z > 0;
      const wl = useRest ? wlRaw.map((w) => w / (1 + (z as number))) : wlRaw;
      let flux: number[] = flRaw;
      if (normalize) {
        // Match the source-page viewer: divide by |median|, floored to avoid
        // blow-up on faint / badly-sky-subtracted spectra.
        const norm = Math.abs(median(flRaw) ?? 0) || 1e-20;
        flux = flRaw.map((f) => f / norm);
      }
      if (clipPct > 0) {
        // Winsorize to [clipPct, 100-clipPct] percentiles: cosmic-ray / sky-line
        // spikes otherwise set the whole y-scale across a multi-object stack.
        const lo = percentile(flux, clipPct);
        const hi = percentile(flux, 100 - clipPct);
        if (lo != null && hi != null && hi > lo) {
          flux = flux.map((f) => (f < lo ? lo : f > hi ? hi : f));
        }
      }
      if (smoothWindow > 0) flux = smoothing_func(flux, smoothWindow) ?? flux;
      recs.push({ sourceId: sp.obj_id, phase: mjd - t0, wl, flux });
    });
    recs.sort((a, b) => a.phase - b.phase);
    return recs;
  }, [data, meta, t0Mode, restFrame, normalize, clipPct, smoothWindow]);

  // Cap the drawn traces, sampling evenly across the phase-sorted list so the
  // full phase range stays represented instead of dropping the latest spectra.
  const rendered = useMemo(() => {
    if (records.length <= MAX_SPECTRA) return records;
    const step = records.length / MAX_SPECTRA;
    return Array.from(
      { length: MAX_SPECTRA },
      (_, i) => records[Math.floor(i * step)] as SpectrumRecord,
    );
  }, [records]);

  const { traces, layout } = useMemo(() => {
    const phases = rendered.map((r) => r.phase);
    const pmin = phases.length ? Math.min(...phases) : 0;
    const pmax = phases.length ? Math.max(...phases) : 1;
    const span = pmax - pmin || 1;

    // Waterfall offset scaled to the typical trace amplitude (robust 5-95
    // spread), so it works whatever the normalize/clip/smooth settings produce.
    const spreads = rendered
      .map((r) => {
        const lo = percentile(r.flux, 5);
        const hi = percentile(r.flux, 95);
        return lo != null && hi != null ? hi - lo : 0;
      })
      .filter((s) => s > 0);
    const baseSpread = median(spreads) ?? 1;
    const offsetStep =
      display === "waterfall" ? baseSpread * 1.1 * offsetMult : 0;

    // Robust default wavelength range so one spectrum spanning e.g. 3000-24000 A
    // doesn't squash everything; either explicit bound independently overrides it.
    let xLo: number | undefined;
    let xHi: number | undefined;
    if (rendered.length) {
      xLo =
        percentile(
          rendered.map((r) => Math.min(...r.wl)),
          5,
        ) ?? undefined;
      xHi =
        percentile(
          rendered.map((r) => Math.max(...r.wl)),
          90,
        ) ?? undefined;
    }
    const wlLo = parseFloat(wlMin);
    const wlHi = parseFloat(wlMax);
    if (Number.isFinite(wlLo)) xLo = wlLo;
    if (Number.isFinite(wlHi)) xHi = wlHi;
    const xRange: [number, number] | undefined =
      xLo != null && xHi != null && xHi > xLo ? [xLo, xHi] : undefined;

    // Color mode shares one flux axis: clamp its range to robust percentiles of
    // a subsample so a lone survivor spike can't compress everything.
    let yRange: [number, number] | undefined;
    if (display === "color" && rendered.length) {
      const sample: number[] = [];
      rendered.forEach((r) => {
        const step = Math.max(1, Math.floor(r.flux.length / 50));
        for (let i = 0; i < r.flux.length; i += step)
          sample.push(r.flux[i] as number);
      });
      const lo = percentile(sample, 1);
      const hi = percentile(sample, 99);
      if (lo != null && hi != null && hi > lo) {
        const pad = (hi - lo) * 0.05;
        yRange = [lo - pad, hi + pad];
      }
    }

    const tr = rendered.map((r, i) => {
      const t = (r.phase - pmin) / span;
      const yOffset = i * offsetStep;
      return {
        type: "scattergl",
        mode: "lines",
        name: `${r.sourceId} (${r.phase.toFixed(1)} d)`,
        x: r.wl,
        y: yOffset ? r.flux.map((f) => f + yOffset) : r.flux,
        line: {
          width: 1,
          ...(display === "color" ? { color: phaseColor(t) } : {}),
        },
        hovertemplate:
          `${r.sourceId}<br>phase: ${r.phase.toFixed(1)} d<br>` +
          `λ: %{x:.0f}<br>flux: %{y:.3g}<extra></extra>`,
      };
    });

    return {
      traces: tr,
      layout: {
        xaxis: {
          title: {
            text: restFrame ? "Rest wavelength (Å)" : "Observed wavelength (Å)",
          },
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: {
            text: normalize
              ? display === "waterfall"
                ? "Normalized flux + offset"
                : "Normalized flux"
              : display === "waterfall"
                ? "Flux + offset"
                : "Flux",
          },
          ...(yRange ? { range: yRange } : {}),
        },
        showlegend: false,
        height: 600,
        margin: { t: 10 },
      },
    };
  }, [rendered, display, restFrame, normalize, offsetMult, wlMin, wlMax]);

  const nSources = useMemo(
    () => new Set(rendered.map((r) => r.sourceId)).size,
    [rendered],
  );

  return (
    <Paper sx={{ p: 1 }}>
      <Box
        sx={{
          display: "flex",
          gap: 2,
          alignItems: "center",
          flexWrap: "wrap",
          mb: 1,
        }}
      >
        <FormControl size="small" sx={{ minWidth: "11rem" }}>
          <InputLabel>Phase zero (t0)</InputLabel>
          <Select
            label="Phase zero (t0)"
            value={t0Mode}
            onChange={(e) => setT0Mode(e.target.value as T0Mode)}
          >
            <MenuItem value="first">First detection</MenuItem>
            <MenuItem value="peak">Peak brightness</MenuItem>
            <MenuItem value="tns">TNS discovery</MenuItem>
          </Select>
        </FormControl>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={display}
          onChange={(_e, v) => v && setDisplay(v)}
        >
          <ToggleButton value="waterfall">Waterfall</ToggleButton>
          <ToggleButton value="color">Color by phase</ToggleButton>
        </ToggleButtonGroup>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={restFrame}
              onChange={(e) => setRestFrame(e.target.checked)}
            />
          }
          label="Rest frame"
        />
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={normalize}
              onChange={(e) => setNormalize(e.target.checked)}
            />
          }
          label="Normalize"
        />
        <Box sx={{ width: "9rem", display: "flex", flexDirection: "column" }}>
          <Typography variant="caption">
            Clip spikes: {clipPct === 0 ? "off" : `${clipPct}%`}
          </Typography>
          <Slider
            size="small"
            value={clipPct}
            onChange={(_e, v) => setClipPct(v as number)}
            min={0}
            max={5}
            step={0.5}
            valueLabelDisplay="auto"
          />
        </Box>
        <Box sx={{ width: "9rem", display: "flex", flexDirection: "column" }}>
          <Typography variant="caption">Smoothing: {smoothWindow}</Typography>
          <Slider
            size="small"
            value={smoothWindow}
            onChange={(_e, v) => setSmoothWindow(v as number)}
            min={0}
            max={20}
            step={1}
            valueLabelDisplay="auto"
          />
        </Box>
        {display === "waterfall" && (
          <Box sx={{ width: "9rem", display: "flex", flexDirection: "column" }}>
            <Typography variant="caption">
              Offset: {offsetMult.toFixed(1)}×
            </Typography>
            <Slider
              size="small"
              value={offsetMult}
              onChange={(_e, v) => setOffsetMult(v as number)}
              min={0}
              max={3}
              step={0.1}
              valueLabelDisplay="auto"
            />
          </Box>
        )}
        <TextField
          size="small"
          label="λ min (Å)"
          value={wlMin}
          onChange={(e) => setWlMin(e.target.value)}
          sx={{ width: "6.5rem" }}
        />
        <TextField
          size="small"
          label="λ max (Å)"
          value={wlMax}
          onChange={(e) => setWlMax(e.target.value)}
          sx={{ width: "6.5rem" }}
        />
        {isFetching && <CircularProgress size={20} />}
      </Box>

      <Typography variant="body2" color="textSecondary">
        Showing {rendered.length}
        {records.length > rendered.length ? ` of ${records.length}` : ""}{" "}
        spectra from {nSources} source{nSources === 1 ? "" : "s"}. Sources
        without a {t0Label[t0Mode]} are omitted.
        {data?.truncated
          ? " Result truncated — narrow the selection to see everything."
          : ""}
      </Typography>

      {rendered.length === 0 ? (
        <Typography sx={{ mt: 2 }}>
          {isFetching
            ? "Loading spectra…"
            : "No spectra to display for the current selection."}
        </Typography>
      ) : (
        <Plot
          data={traces as any}
          layout={layout as any}
          useResizeHandler
          style={{ width: "100%" }}
          config={{ displaylogo: false, responsive: true } as any}
        />
      )}
    </Paper>
  );
};

export default SpectraAggregation;

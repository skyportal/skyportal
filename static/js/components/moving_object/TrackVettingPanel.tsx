import { useMemo } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import {
  MeasuredEpoch,
  TrackMeasurement,
} from "../../ducks/moving_object_track";

const Plot = createPlotlyComponent(Plotly);

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

const BAND_COLOR: Record<string, string> = {
  g: "#1b9e77",
  r: "#d95f02",
  i: "#7570b3",
};

/** Every epoch's difference cutout, in time order, labelled with band and SNR. */
const CutoutStrip = ({ detections }: { detections: MeasuredEpoch[] }) => (
  <Box
    sx={{
      display: "flex",
      gap: "0.35rem",
      overflowX: "auto",
      paddingBottom: "0.25rem",
    }}
  >
    {detections.map((d) => (
      <Box key={d.candid} sx={{ textAlign: "center", flex: "0 0 auto" }}>
        {d.png ? (
          <Box
            component="img"
            src={`data:image/png;base64,${d.png}`}
            alt={`epoch ${d.jd}`}
            sx={{ width: "5rem", height: "5rem", display: "block" }}
          />
        ) : (
          <Box
            sx={{
              width: "5rem",
              height: "5rem",
              display: "grid",
              placeItems: "center",
              fontSize: "0.6rem",
              opacity: 0.5,
              border: "1px dashed",
            }}
          >
            no image
          </Box>
        )}
        <Typography
          sx={{ fontSize: "0.65rem", color: BAND_COLOR[d.band ?? ""] }}
        >
          {d.band} {d.snr.toFixed(1)}σ
        </Typography>
        {d.centroid_offset_px > 1 && (
          <Typography sx={{ fontSize: "0.6rem", color: "warning.main" }}>
            off {d.centroid_offset_px.toFixed(0)}px
          </Typography>
        )}
      </Box>
    ))}
  </Box>
);

interface TrackVettingPanelProps {
  measurement: TrackMeasurement;
}

/**
 * Deciding whether a set of detections is one real moving object.
 *
 * The detections carry many object ids because a positional survey renames a
 * mover every visit, so nothing here is keyed on one.
 */
const TrackVettingPanel = ({ measurement }: TrackVettingPanelProps) => {
  const theme = useTheme();
  const { detections, motion, position_angles: angles } = measurement;

  const byBand = useMemo(() => {
    const groups: Record<string, MeasuredEpoch[]> = {};
    detections.forEach((d) => {
      (groups[d.band ?? "?"] ||= []).push(d);
    });
    return groups;
  }, [detections]);

  const t0 = detections[0]?.jd ?? 0;
  const faintest = Math.min(...detections.map((d) => d.snr));
  const offCentre = detections.filter((d) => d.centroid_offset_px > 1).length;
  const disagreeing = measurement.band_flux.filter((p) => !p.agrees).length;
  const first = angles[0];
  const last = angles[angles.length - 1];
  const turn =
    first !== undefined && last !== undefined ? Math.abs(first - last) : 0;

  const axis = {
    gridcolor: theme.palette.divider,
    zerolinecolor: theme.palette.divider,
    color: theme.palette.text.secondary,
  };
  const layout = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: theme.palette.text.primary, size: 10 },
    margin: { l: 44, r: 8, t: 22, b: 36 },
    height: 220,
    showlegend: false,
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <Box sx={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
        <Chip size="small" label={`${measurement.n_detections} detections`} />
        <Chip
          size="small"
          label={`${measurement.arc_days.toFixed(1)} day arc`}
        />
        <Chip
          size="small"
          label={`${measurement.n_object_ids} object ids`}
          title="A positional survey renames a moving object almost every visit"
        />
        <Chip
          size="small"
          color={faintest >= 3 ? "success" : "warning"}
          label={`faintest ${faintest.toFixed(1)}σ`}
        />
        <Chip
          size="small"
          color={offCentre === 0 ? "success" : "warning"}
          label={offCentre === 0 ? "all centred" : `${offCentre} off centre`}
        />
        <Chip size="small" label={`turns ${turn.toFixed(0)}°`} />
        {motion && (
          <Chip
            size="small"
            label={`${motion.rms_arcsec.toFixed(2)}" rms (deg ${motion.degree})`}
            title={`about a degree-${motion.degree} fit through ${motion.n_points} points`}
          />
        )}
        {disagreeing > 0 && (
          <Chip
            size="small"
            color="warning"
            label={`${disagreeing} band mismatch`}
          />
        )}
      </Box>

      {!motion && (
        <Alert severity="info" sx={{ fontSize: "0.75rem" }}>
          Too few detections to fit a motion model. The arc has to grow before a
          residual means anything.
        </Alert>
      )}

      <Paper variant="outlined" sx={{ padding: "0.4rem" }}>
        <Typography
          sx={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.25rem" }}
        >
          Difference cutouts, stretched to each epoch&apos;s own background
        </Typography>
        <CutoutStrip detections={detections} />
      </Paper>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(18rem, 1fr))",
          gap: "0.5rem",
        }}
      >
        <Paper variant="outlined" sx={{ padding: "0.25rem" }}>
          <Plot
            data={[
              {
                x: detections.map((d) => d.ra),
                y: detections.map((d) => d.dec),
                mode: "markers+lines",
                type: "scatter",
                marker: {
                  size: 7,
                  color: detections.map((d) => d.jd - t0),
                  colorscale: "Viridis",
                  showscale: false,
                },
                line: { width: 1, color: theme.palette.divider },
              },
            ]}
            layout={{
              ...layout,
              title: {
                text: "Sky motion (colour is time)",
                font: { size: 11 },
              },
              // RA runs the other way on the sky.
              xaxis: { ...axis, title: { text: "RA" }, autorange: "reversed" },
              yaxis: { ...axis, title: { text: "Dec" } },
            }}
            config={{ displayModeBar: false }}
            style={{ width: "100%" }}
          />
        </Paper>

        <Paper variant="outlined" sx={{ padding: "0.25rem" }}>
          <Plot
            data={Object.entries(byBand).map(([band, rows]) => ({
              x: rows.map((d) => d.jd - t0),
              y: rows.map((d) => d.mag),
              mode: "markers",
              type: "scatter",
              name: band,
              marker: {
                size: 7,
                color: BAND_COLOR[band] ?? theme.palette.text.primary,
              },
            }))}
            layout={{
              ...layout,
              showlegend: true,
              title: { text: "Magnitude by band", font: { size: 11 } },
              xaxis: { ...axis, title: { text: "days from first" } },
              yaxis: { ...axis, title: { text: "mag" }, autorange: "reversed" },
            }}
            config={{ displayModeBar: false }}
            style={{ width: "100%" }}
          />
        </Paper>

        <Paper variant="outlined" sx={{ padding: "0.25rem" }}>
          <Plot
            data={[
              {
                x: detections.slice(1).map((d) => d.jd - t0),
                y: angles,
                mode: "markers+lines",
                type: "scatter",
                marker: { size: 6, color: theme.palette.primary.main },
              },
            ]}
            layout={{
              ...layout,
              title: {
                text: "Position angle along the arc",
                font: { size: 11 },
              },
              xaxis: { ...axis, title: { text: "days from first" } },
              yaxis: { ...axis, title: { text: "degrees" } },
            }}
            config={{ displayModeBar: false }}
            style={{ width: "100%" }}
          />
        </Paper>
      </Box>

      {measurement.failures.length > 0 && (
        <Alert severity="warning" sx={{ fontSize: "0.75rem" }}>
          {measurement.failures.length} detection(s) could not be measured:{" "}
          {measurement.failures[0]?.error}
        </Alert>
      )}
    </Box>
  );
};

export default TrackVettingPanel;

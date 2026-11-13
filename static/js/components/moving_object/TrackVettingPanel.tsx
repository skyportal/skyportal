import { useMemo } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import {
  KnownObjectVerdict,
  MeasuredEpoch,
  TrackLookup,
  TrackMeasurement,
} from "../../ducks/moving_object_track";
import KnownObjectVerdictPanel from "./KnownObjectVerdictPanel";

const Plot = createPlotlyComponent(Plotly);

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

const BAND_COLOR: Record<string, string> = {
  g: "#1b9e77",
  r: "#d95f02",
  i: "#7570b3",
};

const jdToUTC = (jd: number) =>
  new Date((jd - 2440587.5) * 86400000)
    .toISOString()
    .slice(0, 16)
    .replace("T", " ");

const signed = (value: number) =>
  `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(2)}`;

const OrbitElements = ({
  orbit,
}: {
  orbit: NonNullable<TrackLookup["orbit"]>;
}) => {
  const rows: [string, string | null][] = [
    ["a", orbit.a != null ? `${orbit.a.toFixed(4)} au` : null],
    ["e", orbit.e.toFixed(4)],
    ["q", `${orbit.q.toFixed(4)} au`],
    ["i", orbit.incl != null ? `${orbit.incl.toFixed(3)}°` : null],
    ["Ω", orbit.node != null ? `${orbit.node.toFixed(3)}°` : null],
    ["ω", orbit.peri != null ? `${orbit.peri.toFixed(3)}°` : null],
    [
      "M",
      orbit.mean_anomaly != null ? `${orbit.mean_anomaly.toFixed(3)}°` : null,
    ],
    ["Tp", orbit.tp != null ? `${jdToUTC(orbit.tp)} UTC` : null],
    ["Epoch", orbit.epoch_jd != null ? `${jdToUTC(orbit.epoch_jd)} UTC` : null],
    [
      "Fit rms",
      orbit.rms_arcsec != null
        ? `${orbit.rms_arcsec.toFixed(2)}″${orbit.n_fitted != null ? ` over ${orbit.n_fitted} detections` : ""}`
        : null,
    ],
  ];
  return (
    <Paper variant="outlined" sx={{ padding: "0.4rem" }}>
      <Typography
        sx={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.25rem" }}
      >
        Fitted orbit, heliocentric ecliptic J2000
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(11rem, 1fr))",
          columnGap: "1rem",
          rowGap: "0.1rem",
        }}
      >
        {rows
          .filter(([, value]) => value != null)
          .map(([label, value]) => (
            <Typography key={label} sx={{ fontSize: "0.75rem" }}>
              <Box
                component="span"
                sx={{ opacity: 0.65, marginRight: "0.4rem" }}
              >
                {label}
              </Box>
              {value}
            </Typography>
          ))}
      </Box>
    </Paper>
  );
};

/** Every epoch's difference cutout, in time order, labelled with band and SNR. */
const CutoutStrip = ({
  detections,
  expectedRms,
  excluded,
  onToggle,
}: {
  detections: MeasuredEpoch[];
  expectedRms: number | null;
  excluded: string[];
  onToggle: (candid: string) => void;
}) => (
  <Box
    sx={{
      display: "flex",
      gap: "0.35rem",
      overflowX: "auto",
      paddingBottom: "0.25rem",
    }}
  >
    {detections.map((d) => (
      <Box
        key={d.candid}
        sx={{
          textAlign: "center",
          flex: "0 0 auto",
          opacity: excluded.includes(d.candid) ? 0.35 : 1,
        }}
      >
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
        {d.residual_ra != null && d.residual_dec != null && (
          <Typography
            title="Observed minus computed RA, Dec (arcsec)"
            sx={{
              fontSize: "0.6rem",
              color:
                expectedRms != null &&
                Math.hypot(d.residual_ra, d.residual_dec) > 3 * expectedRms
                  ? "warning.main"
                  : "text.secondary",
            }}
          >
            {signed(d.residual_ra)} {signed(d.residual_dec)}
          </Typography>
        )}
        {d.fwhm_ratio != null && (
          <Typography
            title="FWHM over the PSF of the exposure"
            sx={{ fontSize: "0.6rem", color: "text.secondary" }}
          >
            fwhm ×{d.fwhm_ratio.toFixed(2)}
          </Typography>
        )}
        <Button
          size="small"
          onClick={() => onToggle(d.candid)}
          sx={{ fontSize: "0.6rem", minWidth: 0, padding: "0 0.25rem" }}
        >
          {excluded.includes(d.candid) ? "Include" : "Exclude"}
        </Button>
      </Box>
    ))}
  </Box>
);

interface TrackVettingPanelProps {
  track: TrackLookup;
  measurement: TrackMeasurement;
  knownObject: KnownObjectVerdict | null | undefined;
  checkingKnown: boolean;
  excluded: string[];
  onToggleExcluded: (candid: string) => void;
}

/**
 * Deciding whether a set of detections is one real moving object.
 *
 * The detections carry many object ids because a positional survey renames a
 * mover every visit, so nothing here is keyed on one.
 */
const TrackVettingPanel = ({
  track,
  measurement,
  knownObject,
  checkingKnown,
  excluded,
  onToggleExcluded,
}: TrackVettingPanelProps) => {
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
  const withResiduals = detections.filter(
    (d) => d.residual_ra != null && d.residual_dec != null,
  );
  const { activity } = track;
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
        {activity && (
          <Chip
            size="small"
            color={activity.possible_comet ? "warning" : "default"}
            label={activity.possible_comet ? "possible comet" : "point-like"}
            title={`Median over ${activity.n_detections} untrailed detections: FWHM ${activity.fwhm_ratio.toFixed(2)}x the PSF, classtar ${activity.classtar?.toFixed(2) ?? "?"}`}
          />
        )}
      </Box>

      {!motion && (
        <Alert severity="info" sx={{ fontSize: "0.75rem" }}>
          Too few detections to fit a motion model. The arc has to grow before a
          residual means anything.
        </Alert>
      )}

      <KnownObjectVerdictPanel verdict={knownObject} checking={checkingKnown} />

      {track.orbit && <OrbitElements orbit={track.orbit} />}

      <Paper variant="outlined" sx={{ padding: "0.4rem" }}>
        <Typography
          sx={{ fontSize: "0.75rem", fontWeight: 600, marginBottom: "0.25rem" }}
        >
          Difference cutouts, stretched to each epoch&apos;s own background
          {excluded.length > 0 &&
            `, ${excluded.length} excluded from the MPC submission`}
        </Typography>
        <CutoutStrip
          detections={detections}
          expectedRms={track.orbit?.expected_rms_arcsec ?? null}
          excluded={excluded}
          onToggle={onToggleExcluded}
        />
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

        {withResiduals.length > 0 && (
          <Paper variant="outlined" sx={{ padding: "0.25rem" }}>
            <Plot
              data={[
                {
                  x: withResiduals.map((d) => d.jd - t0),
                  y: withResiduals.map((d) => d.residual_ra),
                  mode: "markers",
                  type: "scatter",
                  name: "RA",
                  marker: { size: 6, color: theme.palette.primary.main },
                },
                {
                  x: withResiduals.map((d) => d.jd - t0),
                  y: withResiduals.map((d) => d.residual_dec),
                  mode: "markers",
                  type: "scatter",
                  name: "Dec",
                  marker: { size: 6, color: theme.palette.secondary.main },
                },
              ]}
              layout={{
                ...layout,
                showlegend: true,
                title: {
                  text: "Residuals from the fitted orbit",
                  font: { size: 11 },
                },
                xaxis: { ...axis, title: { text: "days from first" } },
                yaxis: { ...axis, title: { text: "O-C (arcsec)" } },
              }}
              config={{ displayModeBar: false }}
              style={{ width: "100%" }}
            />
          </Paper>
        )}
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

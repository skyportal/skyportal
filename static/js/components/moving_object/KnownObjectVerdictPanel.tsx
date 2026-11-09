import ErrorOutlinedIcon from "@mui/icons-material/ErrorOutlined";
import HelpOutlinedIcon from "@mui/icons-material/HelpOutlined";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import {
  KnownObjectMatch,
  KnownObjectVerdict,
} from "../../ducks/moving_object_track";

const NearestKnown = ({ objects }: { objects: KnownObjectMatch[] }) => {
  const nearest = [...objects].sort(
    (a, b) => a.nearest_arcsec - b.nearest_arcsec,
  )[0];
  return (
    <Typography sx={{ fontSize: "0.72rem", marginTop: "0.35rem" }}>
      {nearest
        ? `Nearest known: ${nearest.name}, ${nearest.nearest_arcsec.toFixed(0)}″ away${
            nearest.rate_difference_arcsec_per_hour != null
              ? `, motion differs by ${nearest.rate_difference_arcsec_per_hour.toFixed(1)}″/h`
              : ""
          }`
        : "No known object within 6′"}
    </Typography>
  );
};

interface KnownObjectVerdictPanelProps {
  verdict: KnownObjectVerdict | null | undefined;
  checking?: boolean;
}

/**
 * Whether this track is already a known minor planet.
 *
 * Three states, and the third is the one that matters: a check that could not
 * run must never look like one that ran and found nothing, because that is how
 * a known object gets submitted as a discovery.
 */
const KnownObjectVerdictPanel = ({
  verdict,
  checking = false,
}: KnownObjectVerdictPanelProps) => {
  if (!verdict && checking) {
    return (
      <Alert
        severity="info"
        icon={<CircularProgress size="1.1rem" />}
        sx={{ fontSize: "0.8rem" }}
      >
        <AlertTitle sx={{ fontSize: "0.85rem" }}>Checking JPL</AlertTitle>
        JPL takes a few minutes to answer.
      </Alert>
    );
  }

  if (!verdict) {
    return (
      <Alert
        severity="warning"
        icon={<HelpOutlinedIcon />}
        sx={{ fontSize: "0.8rem" }}
      >
        <AlertTitle sx={{ fontSize: "0.85rem" }}>Not checked</AlertTitle>
        No known-object check has been run against this track.
      </Alert>
    );
  }

  const { known, verified, matches, nearby, errors, reason } = verdict;

  // Unverified first: it outranks whatever the check thinks it found.
  if (!verified) {
    return (
      <Alert
        severity="warning"
        icon={<HelpOutlinedIcon />}
        sx={{ fontSize: "0.8rem" }}
      >
        <AlertTitle sx={{ fontSize: "0.85rem" }}>Check did not run</AlertTitle>
        {reason}
        {errors.length > 0 && (
          <Typography
            sx={{ fontSize: "0.7rem", opacity: 0.8, marginTop: "0.25rem" }}
          >
            {errors[0]}
          </Typography>
        )}
        {(nearby ?? []).length > 0 && <NearestKnown objects={nearby} />}
        <Typography sx={{ fontSize: "0.75rem", marginTop: "0.35rem" }}>
          This is not a clean negative. Treat the track as unidentified, not as
          a discovery.
        </Typography>
      </Alert>
    );
  }

  if (known) {
    const match = matches[0];
    return (
      <Alert
        severity="error"
        icon={<ErrorOutlinedIcon />}
        sx={{ fontSize: "0.8rem" }}
      >
        <AlertTitle sx={{ fontSize: "0.85rem" }}>
          Recovery of {match?.name ?? "a known object"}
        </AlertTitle>
        {reason}
        {match && (
          <Typography
            sx={{ fontSize: "0.72rem", opacity: 0.85, marginTop: "0.25rem" }}
          >
            {match.nearest_arcsec.toFixed(0)}&Prime; away, holding to{" "}
            {match.offset_drift_arcsec.toFixed(1)}&Prime; over {match.epochs}{" "}
            epochs
            {match.motion_agrees ? ", and the motion agrees" : ""}.
          </Typography>
        )}
        <NearestKnown objects={[...matches, ...(nearby ?? [])]} />
        <Typography sx={{ fontSize: "0.75rem", marginTop: "0.35rem" }}>
          Already catalogued. Do not submit as a discovery.
        </Typography>
      </Alert>
    );
  }

  return (
    <Alert
      severity="success"
      icon={<NewReleasesOutlinedIcon />}
      sx={{ fontSize: "0.8rem" }}
    >
      <AlertTitle sx={{ fontSize: "0.85rem" }}>Nothing known here</AlertTitle>
      {reason}
      <NearestKnown objects={nearby ?? []} />
      {nearby.length > 0 && (
        <Box sx={{ marginTop: "0.35rem" }}>
          <Typography sx={{ fontSize: "0.72rem", opacity: 0.85 }}>
            Ruled out nearby:
          </Typography>
          {nearby.slice(0, 4).map((object) => (
            <Typography
              key={object.name}
              sx={{ fontSize: "0.7rem", opacity: 0.75 }}
            >
              {object.name} — {object.reason}
            </Typography>
          ))}
        </Box>
      )}
    </Alert>
  );
};

export default KnownObjectVerdictPanel;

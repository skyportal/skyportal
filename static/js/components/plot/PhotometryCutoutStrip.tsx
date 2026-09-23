import { useEffect, useState } from "react";

import CloseIcon from "@mui/icons-material/Close";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import CutoutTriplet from "../broker/CutoutTriplet";

export interface CutoutPin {
  candid: string;
  photometryId: number | null;
  mjd: number | null;
  filter: string | null;
}

interface ResolvedAlert {
  candid: string;
  broker_id: number;
  survey: string | null;
  ra: number | null;
  dec: number | null;
}

/** One pinned epoch: resolves its alert, then shows that alert's cutouts. */
const PinnedCutout = ({
  pin,
  onRemove,
}: {
  pin: CutoutPin;
  onRemove: () => void;
}) => {
  const [alert, setAlert] = useState<ResolvedAlert | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setAlert(null);
    setError(null);

    // A point the broker served that was never saved has no row to look up, so
    // it is resolved by the alert id it arrived carrying.
    const lookup =
      pin.photometryId != null
        ? `/api/brokers/photometry/${pin.photometryId}/alert`
        : `/api/brokers/photometry/alert?candid=${encodeURIComponent(pin.candid)}`;

    fetch(lookup, { headers: { "Content-Type": "application/json" } })
      .then((response) => response.json())
      .then((payload) => {
        if (!alive) return;
        if (payload?.status === "success") {
          setAlert(payload.data);
        } else {
          setError(payload?.message ?? "No cutouts for this point.");
        }
      })
      .catch(() => alive && setError("Could not reach the server."));

    return () => {
      alive = false;
    };
  }, [pin.candid, pin.photometryId]);

  return (
    <Paper variant="outlined" sx={{ padding: "0.4rem", position: "relative" }}>
      <IconButton
        size="small"
        onClick={onRemove}
        sx={{ position: "absolute", top: 0, right: 0 }}
        aria-label="Remove this epoch"
      >
        <CloseIcon sx={{ fontSize: "0.9rem" }} />
      </IconButton>
      <Typography sx={{ fontSize: "0.7rem", fontWeight: 600 }}>
        {pin.mjd != null ? `MJD ${pin.mjd.toFixed(4)}` : "Epoch"}
      </Typography>
      <Typography
        sx={{ fontSize: "0.65rem", opacity: 0.65, marginBottom: "0.25rem" }}
      >
        {[pin.filter, alert?.survey].filter(Boolean).join(" · ") || " "}
      </Typography>
      {error && (
        <Alert
          severity="info"
          sx={{ fontSize: "0.65rem", padding: "0 0.5rem" }}
        >
          {error}
        </Alert>
      )}
      {!error && !alert && <CircularProgress size="1.2rem" />}
      {alert && (
        <CutoutTriplet
          brokerId={alert.broker_id}
          candid={alert.candid}
          survey={alert.survey ?? "ZTF"}
          ra={alert.ra ?? 0}
          dec={alert.dec ?? 0}
          size="6rem"
        />
      )}
    </Paper>
  );
};

interface PhotometryCutoutStripProps {
  pins: CutoutPin[];
  onRemove: (candid: string) => void;
  onClear: () => void;
}

/**
 * The images behind the points someone clicked, kept side by side.
 *
 * Pinned rather than shown one at a time: deciding whether an outburst is real
 * means comparing epochs against each other, which a view that replaces itself
 * on every click cannot do.
 */
const PhotometryCutoutStrip = ({
  pins,
  onRemove,
  onClear,
}: PhotometryCutoutStripProps) => {
  if (pins.length === 0) return null;

  return (
    <Box sx={{ marginTop: "0.5rem" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <Typography sx={{ fontSize: "0.75rem", fontWeight: 600 }}>
          Cutouts ({pins.length})
        </Typography>
        <Button size="small" onClick={onClear} sx={{ fontSize: "0.7rem" }}>
          Clear
        </Button>
      </Box>
      <Box
        sx={{
          display: "flex",
          gap: "0.5rem",
          overflowX: "auto",
          paddingBottom: "0.25rem",
        }}
      >
        {pins.map((pin) => (
          <PinnedCutout
            key={pin.candid}
            pin={pin}
            onRemove={() => onRemove(pin.candid)}
          />
        ))}
      </Box>
    </Box>
  );
};

export default PhotometryCutoutStrip;

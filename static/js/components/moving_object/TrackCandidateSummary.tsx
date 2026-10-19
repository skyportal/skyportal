import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import {
  TrackAnalysis,
  TrackMeasurement,
  useGetMovingObjectTrackQuery,
  useMeasureTrackCutoutsMutation,
  useMeasureTrackGeometryMutation,
} from "../../ducks/moving_object_track";
import TrackVettingPanel from "./TrackVettingPanel";

interface TrackCandidateSummaryProps {
  trackId: string;
  brokerId: number;
  survey?: string;
}

/**
 * A linked track on a candidate, in two tiers.
 *
 * The geometry costs no broker call, so it shows for every candidate. Measuring
 * the pixels means a cutout fetch per epoch, which no scanning page can afford
 * across a screenful, so it waits until someone asks for this one.
 */
const TrackCandidateSummary = ({
  trackId,
  brokerId,
  survey = "ZTF",
}: TrackCandidateSummaryProps) => {
  const { data: track } = useGetMovingObjectTrackQuery({
    trackId,
    brokerId,
    survey,
  });
  const [measureGeometry] = useMeasureTrackGeometryMutation();
  const [measureCutouts, { isLoading: measuring }] =
    useMeasureTrackCutoutsMutation();
  const [geometry, setGeometry] = useState<TrackAnalysis | null>(null);
  const [vetting, setVetting] = useState<TrackMeasurement | null>(null);

  useEffect(() => {
    let alive = true;
    setGeometry(null);
    setVetting(null);
    if (!track?.detections?.length) return undefined;
    measureGeometry({
      detections: track.detections,
      broker_id: brokerId,
      survey,
    })
      .unwrap()
      .then((result) => alive && setGeometry(result))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [track, brokerId, survey, measureGeometry]);

  if (!track) return null;

  const openVetting = async () => {
    try {
      setVetting(
        await measureCutouts({
          detections: track.detections,
          broker_id: brokerId,
          survey,
        }).unwrap(),
      );
    } catch {
      setVetting(null);
    }
  };

  const turn =
    geometry && geometry.position_angles.length > 1
      ? Math.abs(
          (geometry.position_angles[0] ?? 0) -
            (geometry.position_angles[geometry.position_angles.length - 1] ??
              0),
        )
      : null;

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.3rem",
        alignItems: "center",
      }}
    >
      <Chip size="small" label={track.id} />
      <Chip size="small" label={`${track.n_detections ?? "?"} det`} />
      <Chip size="small" label={`${track.n_nights ?? "?"} nights`} />
      {track.arc_days != null && (
        <Chip size="small" label={`${track.arc_days.toFixed(1)} d arc`} />
      )}
      {track.designation && (
        <Chip size="small" color="info" label={`known: ${track.designation}`} />
      )}
      {turn != null && (
        <Chip size="small" label={`turns ${turn.toFixed(0)}°`} />
      )}
      {/* A residual on a three-point arc is a forced fit, so it is not shown. */}
      {geometry?.motion && geometry.motion.n_points > 4 && (
        <Chip
          size="small"
          label={`${geometry.motion.rms_arcsec.toFixed(2)}" rms`}
          title={`degree ${geometry.motion.degree} through ${geometry.motion.n_points} points`}
        />
      )}
      {track.members_withheld > 0 && (
        <Chip
          size="small"
          color="warning"
          label={`${track.members_withheld} not visible`}
          title="Detections your streams do not cover, so this arc is partial"
        />
      )}
      {vetting?.known_object && (
        <Chip
          size="small"
          color={
            !vetting.known_object.verified
              ? "warning"
              : vetting.known_object.known
                ? "error"
                : "success"
          }
          label={
            !vetting.known_object.verified
              ? "check failed"
              : vetting.known_object.known
                ? `known: ${vetting.known_object.matches[0]?.name ?? "yes"}`
                : "nothing known"
          }
          title={vetting.known_object.reason}
        />
      )}
      <Button size="small" onClick={openVetting} disabled={measuring}>
        {measuring ? <CircularProgress size="0.9rem" /> : "Vet cutouts"}
      </Button>

      <Dialog
        open={vetting != null}
        onClose={() => setVetting(null)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Vetting {track.id}</DialogTitle>
        <DialogContent>
          {vetting && <TrackVettingPanel measurement={vetting} />}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default TrackCandidateSummary;

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetSharingServicesQuery } from "../../ducks/sharingServices";
import {
  useGetTrackMPCQuery,
  useSubmitTrackToMPCMutation,
} from "../../ducks/moving_object_track";

interface TrackMPCSubmitProps {
  trackId: string;
  brokerId: number;
  objId: string;
}

const ACTIVE_STATUSES = ["pending", "processing", "submitted"];

const SUBMISSION_TYPES = [
  { value: "regular", label: "Regular" },
  { value: "neo_candidate", label: "NEO candidate" },
  { value: "new_comet", label: "New comet" },
] as const;

type SubmissionType = (typeof SUBMISSION_TYPES)[number]["value"];

const errorMessage = (error: unknown) => {
  const e = error as { error?: string; data?: { message?: string } };
  return e?.data?.message ?? e?.error ?? "Cannot build the submission";
};

const TrackMPCSubmit = ({ trackId, brokerId, objId }: TrackMPCSubmitProps) => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [serviceId, setServiceId] = useState<number | "">("");
  const [submitter, setSubmitter] = useState("");
  const [draft, setDraft] = useState<string | null>(null);
  const [submissionType, setSubmissionType] =
    useState<SubmissionType>("regular");

  const { data: services = [] } = useGetSharingServicesQuery(undefined, {
    skip: !open,
  });
  const mpcServices = services.filter((s) => s.enable_sharing_with_mpc);
  const onlyServiceId = mpcServices.length === 1 ? mpcServices[0]?.id : null;

  const {
    data: preview,
    error,
    isFetching,
  } = useGetTrackMPCQuery(
    {
      trackId,
      brokerId,
      sharingServiceId: serviceId === "" ? undefined : serviceId,
      submitter: submitter || undefined,
    },
    { skip: !open },
  );
  const [submit, { isLoading: submitting }] = useSubmitTrackToMPCMutation();

  useEffect(() => {
    if (serviceId === "" && onlyServiceId != null) setServiceId(onlyServiceId);
  }, [serviceId, onlyServiceId]);

  useEffect(() => {
    if (draft === null && preview?.submitter) setDraft(preview.submitter);
  }, [draft, preview?.submitter]);

  const active = preview?.submissions.find((s) =>
    ACTIVE_STATUSES.includes(s.mpc_status ?? ""),
  );

  const onSubmit = async () => {
    if (serviceId === "") return;
    const result = await submit({
      trackId,
      sharing_service_id: serviceId,
      obj_id: objId,
      broker_id: brokerId,
      submitter: draft || undefined,
      submission_type: submissionType,
    });
    if ("error" in result) return;
    dispatch(showNotification(`${trackId} queued for the MPC`));
    setOpen(false);
  };

  return (
    <>
      <Button size="small" variant="contained" onClick={() => setOpen(true)}>
        Submit to MPC
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Submit {trackId} to the MPC</DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
        >
          {preview?.submissions.map((s) => (
            <Typography key={s.id} variant="body2">
              {s.created_at.slice(0, 16).replace("T", " ")}{" "}
              {s.submitter ?? s.username}: {s.mpc_status}
              {s.mpc_submission_id ? ` (${s.mpc_submission_id})` : ""}
            </Typography>
          ))}
          {mpcServices.length === 0 ? (
            <Alert severity="info">
              None of your sharing services submits to the MPC.
            </Alert>
          ) : (
            <TextField
              select
              size="small"
              label="Sharing service"
              value={serviceId}
              onChange={(e) => setServiceId(Number(e.target.value))}
              sx={{ mt: "0.5rem" }}
            >
              {mpcServices.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                  {s.testing ? " (testing)" : ""}
                </MenuItem>
              ))}
            </TextField>
          )}
          <TextField
            size="small"
            label="Submitter"
            value={draft ?? ""}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => setSubmitter(draft ?? "")}
          />
          <TextField
            select
            size="small"
            label="Type"
            value={submissionType}
            onChange={(e) =>
              setSubmissionType(e.target.value as SubmissionType)
            }
          >
            {SUBMISSION_TYPES.map((t) => (
              <MenuItem key={t.value} value={t.value}>
                {t.label}
              </MenuItem>
            ))}
          </TextField>
          {error && serviceId !== "" && (
            <Alert severity="error">{errorMessage(error)}</Alert>
          )}
          {(preview?.members_withheld ?? 0) > 0 && (
            <Alert severity="warning">
              {preview?.members_withheld} detections you cannot see are left
              out.
            </Alert>
          )}
          {preview?.psv && (
            <Box
              component="pre"
              sx={{
                fontSize: "0.7rem",
                overflowX: "auto",
                m: 0,
                p: "0.5rem",
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
              }}
            >
              {preview.psv}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={onSubmit}
            disabled={
              !preview?.psv || isFetching || submitting || Boolean(active)
            }
          >
            {submitting ? (
              <CircularProgress size="0.9rem" />
            ) : (
              `Submit as ${draft ?? ""}`
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default TrackMPCSubmit;

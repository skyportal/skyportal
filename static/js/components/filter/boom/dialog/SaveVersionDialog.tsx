import { useState } from "react";
import {
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControlLabel,
  FormHelperText,
  TextField,
} from "@mui/material";

import { shortFid } from "../filterVersions";

interface SaveVersionDialogProps {
  open: boolean;
  saving: boolean;
  filter?: any;
  onClose: () => void;
  onSave: (comment: string, setAsActive: boolean) => Promise<boolean>;
}

const SaveVersionDialog = ({
  open,
  saving,
  filter,
  onClose,
  onSave,
}: SaveVersionDialogProps) => {
  const [comment, setComment] = useState("");
  const [setAsActive, setSetAsActive] = useState(true);
  const activeFid = filter?.fv?.length ? filter.active_fid : null;

  const handleSave = async () => {
    if (saving) return;
    if (await onSave(comment.trim(), !!activeFid && setAsActive)) {
      setComment("");
      setSetAsActive(true);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Save a new version</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Say what changed and why. It is shown in the version history, so
          anyone looking back at this filter knows what happened.
        </DialogContentText>
        <TextField
          autoFocus
          multiline
          fullWidth
          minRows={3}
          maxRows={10}
          margin="dense"
          label="Comment"
          placeholder="e.g. Raised the drb cut: too many bogus candidates last night"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSave();
          }}
        />
        {activeFid && (
          <>
            <FormControlLabel
              sx={{ mt: 1 }}
              control={
                <Checkbox
                  checked={setAsActive}
                  onChange={(e) => setSetAsActive(e.target.checked)}
                />
              }
              label="Switch to the new version"
            />
            <FormHelperText sx={{ mt: 0 }}>
              {!setAsActive
                ? `Version ${shortFid(activeFid)} stays active. You can switch to the new version later from the version menu.`
                : filter.active
                  ? `Version ${shortFid(activeFid)} keeps running while the new version is validated, then the filter switches to it automatically.`
                  : "Validate the new version before turning the filter on. Validation starts right after saving."}
            </FormHelperText>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saving}
          startIcon={saving ? <CircularProgress size={16} /> : undefined}
        >
          {saving ? "Saving…" : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SaveVersionDialog;

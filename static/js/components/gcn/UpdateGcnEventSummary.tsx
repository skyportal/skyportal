import { useEffect, useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SaveIcon from "@mui/icons-material/Save";
import ClearIcon from "@mui/icons-material/Clear";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import { useUpdateGcnEventMutation } from "../../ducks/gcnEvent";

const useStyles = makeStyles()(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "1rem",
    cursor: "pointer",
  },
}));

interface UpdateGcnEventSummaryProps {
  dateobs: string;
  summary?: string | null;
  summaryHistory?: { summary?: string | null; is_bot?: boolean }[] | null;
  showAISummaries?: boolean;
}

const UpdateGcnEventSummary = ({
  dateobs,
  summary = null,
  summaryHistory = null,
  showAISummaries = true,
}: UpdateGcnEventSummaryProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [updateGcnEvent] = useUpdateGcnEventMutation();
  const [text, setText] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(false);
    let summaries = (summaryHistory || []).filter((entry) => entry?.summary);
    if (showAISummaries === false) {
      summaries = summaries.filter((entry) => entry?.is_bot === false);
    }
    setText(summaries[0]?.summary ?? "");
  }, [summaryHistory, showAISummaries]);

  const handleChange = (e: any) => {
    setText(e.target.value);
    setInvalid(!String(e.target.value).trim());
  };

  const handleSubmit = async (value: string | null) => {
    setIsSubmitting(true);
    try {
      await updateGcnEvent({
        dateobs,
        payload: { summary: value || null },
      }).unwrap();
      dispatch(showNotification("Event summary successfully updated."));
      setDialogOpen(false);
    } catch {
      // error notification handled by the baseQuery
    }
    setIsSubmitting(false);
  };

  return (
    <>
      <Tooltip title="Update Summary">
        <span>
          <EditIcon
            data-testid="updateGcnSummaryIconButton"
            fontSize="small"
            className={classes.editIcon}
            onClick={() => {
              setDialogOpen(true);
            }}
          />
        </span>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        fullWidth
        maxWidth="lg"
        onClose={() => setDialogOpen(false)}
      >
        <DialogTitle>Update Summary</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a valid summary" />
            )}
            <TextField
              data-testid="updateGcnSummaryTextfield"
              size="small"
              label="summary"
              value={text}
              name="summary"
              minRows={2}
              fullWidth
              multiline
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => handleSubmit(text)}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateGcnSummarySubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
          <div className={classes.saveButton}>
            <Tooltip title="Clear the event summary (set to null)">
              <span>
                <Button
                  primary
                  onClick={() => handleSubmit(null)}
                  endIcon={<ClearIcon />}
                  size="large"
                  data-testid="nullifyGcnSummaryButton"
                  disabled={isSubmitting || !summary}
                >
                  Clear
                </Button>
              </span>
            </Tooltip>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UpdateGcnEventSummary;

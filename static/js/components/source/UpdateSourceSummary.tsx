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
import * as sourceActions from "../../ducks/source";

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

interface UpdateSourceSummaryProps {
  source: {
    id?: string;
    summary?: string | null;
    summary_history?: any[];
  };
  showAISummaries?: boolean;
}

const UpdateSourceSummary = ({
  source,
  showAISummaries = true,
}: UpdateSourceSummaryProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [state, setState] = useState<any>({});

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(false);
    let summaries = source?.summary_history || [];
    summaries = [...summaries].filter(
      (summary) => summary?.summary && summary?.summary !== null,
    );
    if (showAISummaries === false) {
      summaries = [...summaries].filter((summary) => summary?.is_bot === false);
    }
    setState({
      summary: summaries?.length > 0 ? summaries[0].summary : "",
    });
  }, [source, showAISummaries, setInvalid]);

  const handleChange = (e: any) => {
    const newState: any = {};
    newState[e.target.name] = e.target.value;
    const value = String(e.target.value).trim();
    if (e.target.name === "summary") {
      setInvalid(!value);
    }
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState: any) => {
    setIsSubmitting(true);
    const newState: any = {};
    newState.summary = subState.summary ? subState.summary : null;
    const result: any = await dispatch(
      sourceActions.updateSource(source.id!, {
        ...newState,
      }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Source summary successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <Tooltip title="Update Summary">
        <span>
          <EditIcon
            data-testid="updateSummaryIconButton"
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
              data-testid="updateSummaryTextfield"
              size="small"
              label="summary"
              value={state.summary}
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
              onClick={() => {
                handleSubmit(state);
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateSummarySubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
          <div className={classes.saveButton}>
            <Tooltip title="Clear source summary (set to null)">
              <span>
                <Button
                  primary
                  onClick={() => {
                    handleSubmit({ summary: null });
                  }}
                  endIcon={<ClearIcon />}
                  size="large"
                  data-testid="nullifySummaryButton"
                  disabled={isSubmitting || source.summary === null}
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

export default UpdateSourceSummary;

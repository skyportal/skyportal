import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import ClearIcon from "@mui/icons-material/Clear";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import FormValidationError from "./FormValidationError";
import * as sourceActions from "../ducks/source";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

const UpdateSourceSummary = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [state, setState] = useState({
    summary:
      source?.summary_history && source?.summary_history.length > 0
        ? source?.summary_history[0].summary // eslint-disable-line react/prop-types
        : "",
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      false,
    );
    setState({
      summary:
        source?.summary_history && source?.summary_history.length > 0
          ? source?.summary_history[0].summary // eslint-disable-line react/prop-types
          : "",
    });
  }, [source, setInvalid]);

  const handleChange = (e) => {
    const newState = {};
    newState[e.target.name] = e.target.value;
    const value = String(e.target.value).trim();
    if (e.target.name === "summary") {
      // eslint-disable-next-line no-restricted-globals
      setInvalid(!value);
    }
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState) => {
    setIsSubmitting(true);
    const newState = {};
    newState.summary = subState.summary ? subState.summary : null;
    const result = await dispatch(
      sourceActions.updateSource(source.id, {
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
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
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

UpdateSourceSummary.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    summary: PropTypes.string,
    summary_history: PropTypes.arrayOf(PropTypes.shape({})),
  }).isRequired,
};

export default UpdateSourceSummary;

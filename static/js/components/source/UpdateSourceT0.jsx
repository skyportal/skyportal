import React, { useState } from "react";
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
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import * as sourceActions from "../../ducks/source";

const useStyles = makeStyles(() => ({
  formInput: {
    marginTop: "0.5rem",
  },
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

const UpdateSourceT0 = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [t0, setT0] = useState(source.t0 ? String(source.t0) : "");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (clear) => {
    setIsSubmitting(true);
    const result = await dispatch(
      sourceActions.updateSource(source.id, {
        t0: clear ? null : t0,
      }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      if (clear) {
        setT0("");
      }
      dispatch(showNotification("Source t0 successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <EditIcon
        data-testid="updateT0IconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Update T0</DialogTitle>
        <DialogContent>
          <div>
            {(!t0.trim() || isNaN(t0)) && (
              <FormValidationError message="Please enter a valid float" />
            )}
            <TextField
              className={classes.formInput}
              data-testid="updateT0Textfield"
              size="small"
              label="First detection time(mjd)"
              value={t0}
              name="t0"
              onChange={(event) => setT0(event.target.value)}
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => handleSubmit(false)}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateT0SubmitButton"
              disabled={isSubmitting || !t0.trim() || isNaN(t0)}
            >
              Save
            </Button>
          </div>
          <div className={classes.saveButton}>
            <Tooltip title="Clear source t0 value (set to null)">
              <span>
                <Button
                  primary
                  onClick={() => handleSubmit(true)}
                  endIcon={<ClearIcon />}
                  size="large"
                  data-testid="nullifyT0Button"
                  disabled={isSubmitting || source.t0 === null}
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

UpdateSourceT0.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    t0: PropTypes.number,
  }).isRequired,
};

export default UpdateSourceT0;

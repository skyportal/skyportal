import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@material-ui/icons/Edit";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Button from "@material-ui/core/Button";
import { makeStyles } from "@material-ui/core/styles";
import SaveIcon from "@material-ui/icons/Save";
import ClearIcon from "@material-ui/icons/Clear";
import Tooltip from "@material-ui/core/Tooltip";
import TextField from "@material-ui/core/TextField";

import { showNotification } from "baselayer/components/Notifications";
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

const UpdateSourceRedshift = ({ source }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [state, setState] = useState({
    redshift: source.redshift ? String(source.redshift) : "",
    redshift_error: source.redshift_error ? String(source.redshift_error) : "",
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      !String(source.redshift) || isNaN(String(source.redshift))
    );
    setState({
      redshift: source.redshift ? String(source.redshift) : "",
      redshift_error: source.redshift_error
        ? String(source.redshift_error)
        : "",
    });
  }, [source, setInvalid]);

  const handleChange = (e) => {
    const newState = {};
    newState[e.target.name] = e.target.value;
    const value = String(e.target.value).trim();
    if (e.target.name === "redshift") {
      // eslint-disable-next-line no-restricted-globals
      setInvalid(!value || isNaN(value));
    }
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState) => {
    setIsSubmitting(true);
    const newState = {};
    newState.redshift = subState.redshift ? subState.redshift : null;
    newState.redshift_error = subState.redshift_error
      ? subState.redshift_error
      : null;
    const result = await dispatch(
      sourceActions.updateSource(source.id, {
        ...newState,
      })
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Source redshift successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <EditIcon
        data-testid="updateRedshiftIconButton"
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
        <DialogTitle>Update Redshift</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a valid float" />
            )}
            <TextField
              data-testid="updateRedshiftTextfield"
              size="small"
              label="z"
              value={state.redshift}
              name="redshift"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updateRedshiftErrorTextfield"
              size="small"
              label="z_err"
              value={state.redshift_error}
              name="redshift_error"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              color="primary"
              onClick={() => {
                handleSubmit(state);
              }}
              startIcon={<SaveIcon />}
              size="large"
              data-testid="updateRedshiftSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
          <div className={classes.saveButton}>
            <Tooltip title="Clear source redshift value (set to null)">
              <Button
                color="primary"
                onClick={() => {
                  handleSubmit({ redshift: null, redshift_error: null });
                }}
                startIcon={<ClearIcon />}
                size="large"
                data-testid="nullifyRedshiftButton"
                disabled={isSubmitting || source.redshift === null}
              >
                Clear
              </Button>
            </Tooltip>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateSourceRedshift.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    redshift: PropTypes.number,
    redshift_error: PropTypes.number,
  }).isRequired,
};

export default UpdateSourceRedshift;

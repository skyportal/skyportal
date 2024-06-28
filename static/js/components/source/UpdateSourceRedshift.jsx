import React, { useEffect, useState } from "react";
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
      !String(source.redshift) || isNaN(String(source.redshift)),
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
      }),
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
              secondary
              onClick={() => {
                handleSubmit(state);
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateRedshiftSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
          <div className={classes.saveButton}>
            <Tooltip title="Clear source redshift value (set to null)">
              <span>
                <Button
                  primary
                  onClick={() => {
                    handleSubmit({ redshift: null, redshift_error: null });
                  }}
                  endIcon={<ClearIcon />}
                  size="large"
                  data-testid="nullifyRedshiftButton"
                  disabled={isSubmitting || source.redshift === null}
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

UpdateSourceRedshift.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    redshift: PropTypes.number,
    redshift_error: PropTypes.number,
  }).isRequired,
};

export default UpdateSourceRedshift;

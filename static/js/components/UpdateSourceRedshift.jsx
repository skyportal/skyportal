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
  const [state, setState] = useState(
    source.redshift ? String(source.redshift) : ""
  );
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    // eslint-disable-next-line no-restricted-globals
    setInvalid(!String(source.redshift) || isNaN(String(source.redshift)));
    setState(source.redshift ? String(source.redshift) : "");
  }, [source, setInvalid]);

  const handleChange = (e) => {
    const value = String(e.target.value).trim();
    // eslint-disable-next-line no-restricted-globals
    setInvalid(!value || isNaN(value));
    setState(value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const result = await dispatch(
      sourceActions.updateSource(source.id, { redshift: state })
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
              value={state}
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              color="primary"
              onClick={handleSubmit}
              startIcon={<SaveIcon />}
              size="large"
              data-testid="updateRedshiftSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
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
  }).isRequired,
};

export default UpdateSourceRedshift;

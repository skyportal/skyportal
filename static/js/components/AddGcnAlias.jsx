import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import FormValidationError from "./FormValidationError";
import * as gcnEventActions from "../ducks/gcnEvent";

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

const AddGcnAlias = ({ gcnEvent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [alias, setAlias] = useState(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      gcnEvent?.aliases?.includes(alias),
    );
  }, [gcnEvent, setInvalid, alias]);

  const handleChange = (e) => {
    setAlias(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const result = await dispatch(
      gcnEventActions.postGcnAlias(gcnEvent.dateobs, { alias }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("GCN Event Alias successfully added."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <AddIcon
        data-testid="addGcnEventAliasIconButton"
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
        <DialogTitle>Add Alias</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a new alias" />
            )}
            <TextField
              data-testid="addAliasTextfield"
              size="small"
              label="alias"
              name="alias"
              onChange={handleChange}
              type="string"
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit();
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="addAliasSubmitButton"
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

AddGcnAlias.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    aliases: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
};

export default AddGcnAlias;

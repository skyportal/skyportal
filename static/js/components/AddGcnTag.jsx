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
import * as gcnTagsActions from "../ducks/gcnTags";

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

const AddGcnTag = ({ gcnEvent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [tag, setTag] = useState(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      gcnEvent?.tags?.includes(tag),
    );
  }, [gcnEvent, setInvalid, tag]);

  const handleChange = (e) => {
    setTag(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const result = await dispatch(
      gcnTagsActions.postGcnTag({ dateobs: gcnEvent.dateobs, text: tag }),
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("GCN Event Tag successfully added."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <AddIcon
        data-testid="addGcnEventTagIconButton"
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
        <DialogTitle>Add Tag</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a new tag" />
            )}
            <TextField
              data-testid="addTagTextfield"
              size="small"
              label="tag"
              name="tag"
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
              data-testid="addTagSubmitButton"
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

AddGcnTag.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string).isRequired,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      }),
    ),
  }).isRequired,
};

export default AddGcnTag;

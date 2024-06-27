import React from "react";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "./Button";

const ConfirmDeletionDialog = ({
  deleteFunction,
  dialogOpen,
  closeDialog,
  resourceName,
}) => (
  <Dialog sx={{ "z-index": 99999 }} open={dialogOpen} onClose={closeDialog}>
    <DialogTitle>Delete {resourceName}?</DialogTitle>
    <DialogContent>
      Are you sure you want to delete this/these {resourceName}?
    </DialogContent>
    <DialogActions>
      <Button secondary autoFocus onClick={closeDialog}>
        Dismiss
      </Button>
      <Button primary onClick={() => deleteFunction()}>
        Confirm
      </Button>
    </DialogActions>
  </Dialog>
);

ConfirmDeletionDialog.propTypes = {
  deleteFunction: PropTypes.func.isRequired,
  dialogOpen: PropTypes.bool.isRequired,
  closeDialog: PropTypes.func.isRequired,
  resourceName: PropTypes.string.isRequired,
};

export default ConfirmDeletionDialog;

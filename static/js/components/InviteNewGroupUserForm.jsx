import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import TextField from "@material-ui/core/TextField";
import Button from "@material-ui/core/Button";
import Dialog from "@material-ui/core/Dialog";
import DialogActions from "@material-ui/core/DialogActions";
import DialogContent from "@material-ui/core/DialogContent";
import DialogContentText from "@material-ui/core/DialogContentText";
import DialogTitle from "@material-ui/core/DialogTitle";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";
import * as invitationsActions from "../ducks/invitations";

const useStyles = makeStyles(() => ({
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

const InviteNewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const [formState, setFormState] = useState({
    newUserEmail: "",
    admin: false,
  });
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false);
  const classes = useStyles();

  const handleClickSubmit = async () => {
    const result = await dispatch(
      invitationsActions.inviteUser({
        userEmail: formState.newUserEmail,
        groupIDs: [group_id],
        groupAdmin: [formState.admin],
        streamIDs: null,
      })
    );
    if (result.status === "success") {
      dispatch(
        showNotification(
          `Invitation successfully sent to ${formState.newUserEmail}`
        )
      );
      setFormState({
        newUserEmail: "",
        admin: false,
      });
    }
  };

  const toggleAdmin = (event) => {
    setFormState({
      ...formState,
      admin: event.target.checked,
    });
  };

  return (
    <div>
      <Typography className={classes.heading}>
        Invite a new user to the site and add them to this group
      </Typography>
      <div style={{ paddingBottom: "1rem" }}>
        <TextField
          id="newUserEmail"
          value={formState?.newUserEmail || ""}
          onChange={(event) =>
            setFormState({ ...formState, newUserEmail: event.target.value })
          }
          label="Enter user email"
        />
      </div>
      <input
        type="checkbox"
        checked={formState?.admin || false}
        onChange={toggleAdmin}
      />
      Group Admin &nbsp;&nbsp;
      <Button
        onClick={() => setConfirmDialogOpen(true)}
        variant="contained"
        size="small"
        disableElevation
      >
        Invite new user
      </Button>
      <Dialog
        open={confirmDialogOpen}
        onClose={() => {
          setConfirmDialogOpen(false);
        }}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          Invite new user and add to this group?
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Click Confirm to invite specified user and grant them access to this
            group.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setConfirmDialogOpen(false);
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={() => {
              setConfirmDialogOpen(false);
              handleClickSubmit();
            }}
            color="primary"
            autoFocus
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};
InviteNewGroupUserForm.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default InviteNewGroupUserForm;

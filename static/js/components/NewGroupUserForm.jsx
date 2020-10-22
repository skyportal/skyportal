import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import TextField from "@material-ui/core/TextField";
import Autocomplete, {
  createFilterOptions,
} from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import Dialog from "@material-ui/core/Dialog";
import DialogActions from "@material-ui/core/DialogActions";
import DialogContent from "@material-ui/core/DialogContent";
import DialogContentText from "@material-ui/core/DialogContentText";
import DialogTitle from "@material-ui/core/DialogTitle";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";
import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";
import * as inviteUsersActions from "../ducks/inviteUsers";

const filter = createFilterOptions();

const useStyles = makeStyles(() => ({
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

const NewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const { invitationsEnabled } = useSelector((state) => state.sysInfo);
  const { allUsers } = useSelector((state) => state.users);
  const [formState, setFormState] = useState({
    newUserEmail: null,
    admin: false,
    invitingNewUser: false,
  });
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false);
  const classes = useStyles();

  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const submitAndResetForm = async () => {
    let result = null;
    if (formState.invitingNewUser && invitationsEnabled) {
      result = await dispatch(
        inviteUsersActions.inviteUser({
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
          newUserEmail: null,
          admin: false,
          invitingNewUser: false,
        });
      }
    } else {
      result = await dispatch(
        groupsActions.addGroupUser({
          username: formState.newUserEmail,
          admin: formState.admin,
          group_id,
        })
      );
      if (result.status === "success") {
        setFormState({
          newUserEmail: null,
          admin: false,
          invitingNewUser: false,
        });
      }
    }
  };

  const handleClickSubmit = (event) => {
    event.preventDefault();
    if (invitationsEnabled && formState.invitingNewUser) {
      // If user clicks confirm, `submitAndResetForm` will be called
      setConfirmDialogOpen(true);
    } else {
      submitAndResetForm();
    }
  };

  const toggleAdmin = (event) => {
    setFormState({
      ...formState,
      admin: event.target.checked,
    });
  };
  const allUserNames = allUsers.map((user) => user.username);

  return (
    <div>
      <Typography className={classes.heading}>
        Add or invite a new user to this group
      </Typography>
      <Autocomplete
        id="newUserEmail"
        value={formState.newUserEmail || ""}
        onChange={(event, newValue) => {
          if (typeof newValue === "string") {
            // The user has entered a username and hit the Enter/Return key
            setFormState({
              newUserEmail: newValue,
              invitingNewUser: !allUserNames.includes(newValue),
            });
          } else if (newValue && newValue.inputValue) {
            // The user has entered a new username and clicked the "Add" option
            setFormState({
              newUserEmail: newValue.inputValue,
              invitingNewUser: true,
            });
          } else {
            setFormState({ newUserEmail: newValue?.username });
          }
        }}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);

          // Suggest the creation of a new value
          if (params.inputValue !== "") {
            filtered.push({
              inputValue: params.inputValue,
              username: `Add "${params.inputValue}"`,
            });
          }

          return filtered;
        }}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        options={allUsers}
        getOptionLabel={(option) => {
          // Value selected with enter, right from the input
          if (typeof option === "string") {
            return option;
          }
          // Add "xxx" option created dynamically
          if (option.inputValue) {
            return option.inputValue;
          }
          // Regular option
          return option.username;
        }}
        renderOption={(option) => option.username}
        style={{ width: 300, paddingBottom: 10 }}
        freeSolo
        renderInput={(params) => (
          // eslint-disable-next-line react/jsx-props-no-spreading
          <TextField {...params} label="Enter user email" />
        )}
      />
      <input
        type="checkbox"
        checked={formState.admin || false}
        onChange={toggleAdmin}
      />
      Group Admin &nbsp;&nbsp;
      <Button
        onClick={handleClickSubmit}
        variant="contained"
        size="small"
        disableElevation
      >
        Add user
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
          Invite new user to this group?
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
              submitAndResetForm();
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
NewGroupUserForm.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default NewGroupUserForm;

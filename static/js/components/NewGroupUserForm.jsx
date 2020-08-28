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

import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";

const filter = createFilterOptions();

const NewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const { allUsers } = useSelector((state) => state.users);
  const [formState, setFormState] = useState({
    newUserEmail: null,
    admin: false,
    invitingNewUser: false,
  });
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false);

  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const submitAndResetForm = () => {
    dispatch(
      groupsActions.addGroupUser({
        username: formState.newUserEmail,
        admin: formState.admin,
        group_id,
      })
    );
    setFormState({
      newUserEmail: null,
      admin: false,
      invitingNewUser: false,
    });
  };

  const handleClickSubmit = (event) => {
    event.preventDefault();
    if (formState.invitingNewUser) {
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

  return (
    <div>
      <Autocomplete
        id="newUserEmail"
        value={formState.newUserEmail}
        onChange={(event, newValue) => {
          if (typeof newValue === "string") {
            setFormState({
              newUserEmail: newValue,
            });
          } else if (newValue && newValue.inputValue) {
            // Create a new value from the user input
            setFormState({
              newUserEmail: newValue.inputValue,
              invitingNewUser: true,
            });
          } else {
            setFormState({ newUserEmail: newValue.username });
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
      <input type="checkbox" checked={formState.admin} onChange={toggleAdmin} />
      Group Admin &nbsp;&nbsp;
      <input type="submit" onClick={handleClickSubmit} value="Add user" />
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

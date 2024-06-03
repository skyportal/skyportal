import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import TextField from "@mui/material/TextField";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";

const filter = createFilterOptions();

const useStyles = makeStyles(() => ({
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
}));

const defaultState = {
  userID: null,
  admin: false,
  canSave: true,
};

const NewGroupUserForm = ({ group_id }) => {
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);
  const [formState, setFormState] = useState(defaultState);
  const classes = useStyles();

  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const handleClickSubmit = async () => {
    if (!formState.userID) {
      dispatch(showNotification("Please select a user", "error"));
    } else {
      const result = await dispatch(
        groupsActions.addGroupUser({
          group_id,
          ...formState,
        }),
      );
      if (result.status === "success") {
        setFormState(defaultState);
      }
    }
  };

  const toggleCheckbox = (event) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  if (!allUsers?.length) {
    return <CircularProgress />;
  }

  return (
    <div>
      <Typography className={classes.heading}>
        Add an existing user to this group
      </Typography>
      <Autocomplete
        data-testid="newGroupUser"
        onChange={(event, newValue) => setFormState({ userID: newValue?.id })}
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          return filtered;
        }}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        options={allUsers}
        getOptionLabel={(option) => option.username}
        sx={{ width: 300, paddingBottom: 10 }}
        defaultValue={null}
        renderInput={(params) => (
          <TextField
            // eslint-disable-next-line react/jsx-props-no-spreading
            {...params}
            label="Username"
            data-testid="newGroupUserTextInput"
          />
        )}
      />
      <input
        type="checkbox"
        checked={formState.canSave}
        onChange={toggleCheckbox}
        name="canSave"
        data-testid="canSaveCheckbox"
      />
      Can save to this group &nbsp;&nbsp;
      <input
        type="checkbox"
        checked={formState.admin}
        onChange={toggleCheckbox}
        name="admin"
        data-testid="adminCheckbox"
      />
      Group Admin &nbsp;&nbsp;
      <Button primary onClick={handleClickSubmit} size="small">
        Add user to group
      </Button>
    </div>
  );
};
NewGroupUserForm.propTypes = {
  group_id: PropTypes.number.isRequired,
};

export default NewGroupUserForm;

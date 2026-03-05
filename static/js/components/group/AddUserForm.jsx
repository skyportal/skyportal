import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import TextField from "@mui/material/TextField";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import CircularProgress from "@mui/material/CircularProgress";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Box from "@mui/material/Box";

import Button from "../Button";
import * as groupsActions from "../../ducks/groups";
import * as usersActions from "../../ducks/users";

const filter = createFilterOptions();

const defaultState = {
  userID: null,
  admin: false,
  canSave: true,
};

const AddUserForm = ({ groupID }) => {
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);
  const [formState, setFormState] = useState(defaultState);
  const [isError, setIsError] = useState(false);
  const [nonMemberUsers, setNonMemberUsers] = useState([]);

  useEffect(() => {
    if (!allUsers.length) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  useEffect(() => {
    setNonMemberUsers(
      allUsers.filter(
        (user) => !user.groups.map((ug) => ug.id).includes(groupID),
      ),
    );
  }, [allUsers, groupID]);

  const handleClickSubmit = async () => {
    if (!formState.userID) {
      setIsError(true);
      return;
    }
    const result = await dispatch(
      groupsActions.addGroupUser({
        group_id: groupID,
        ...formState,
      }),
    );
    if (result.status === "success") {
      setFormState(defaultState);
    }
  };

  const toggleCheckbox = (event) => {
    setFormState({
      ...formState,
      [event.target.name]: event.target.checked,
    });
  };

  if (!allUsers?.length) return <CircularProgress />;

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
      <Autocomplete
        sx={{ minWidth: 320 }}
        onChange={(event, newValue) => {
          setFormState({ ...formState, userID: newValue?.id });
          setIsError(false);
        }}
        filterOptions={(options, params) => filter(options, params)}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        options={nonMemberUsers}
        getOptionLabel={(option) => option.username}
        renderInput={(params) => (
          <TextField
            {...params}
            error={isError}
            helperText={isError ? "Please select a user" : ""}
            label="User to add"
            data-testid="newGroupUserTextInput"
          />
        )}
      />
      <FormControlLabel
        control={
          <Checkbox
            checked={formState.canSave}
            onChange={toggleCheckbox}
            name="canSave"
          />
        }
        label="Can save to this group?"
      />
      <FormControlLabel
        control={
          <Checkbox
            checked={formState.admin}
            onChange={toggleCheckbox}
            name="admin"
          />
        }
        label="Group Admin?"
      />
      <Button primary onClick={handleClickSubmit}>
        Add user
      </Button>
    </Box>
  );
};
AddUserForm.propTypes = {
  groupID: PropTypes.number.isRequired,
};

export default AddUserForm;

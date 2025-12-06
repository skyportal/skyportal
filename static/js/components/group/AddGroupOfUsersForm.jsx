import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import * as groupsActions from "../../ducks/groups";

const AddGroupOfUsersForm = ({ groupID }) => {
  const dispatch = useDispatch();
  const [selectedGroups, setSelectedGroups] = useState([]);
  const { all: groups } = useSelector((state) => state.groups);
  const [isError, setIsError] = useState(false);
  const multiUserGroups = groups.filter((group) => !group.single_user_group);

  const handleSubmit = async () => {
    if (!selectedGroups?.length) {
      setIsError(true);
      return;
    }
    const fromGroupIDs = selectedGroups?.map((g) => g.id);
    const result = await dispatch(
      groupsActions.addAllUsersFromGroups({ toGroupID: groupID, fromGroupIDs }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Successfully added users from specified group(s)"),
      );
      setSelectedGroups([]);
    }
  };

  return (
    <Box sx={{ display: "flex", gap: 2 }}>
      <Autocomplete
        sx={{ minWidth: 400 }}
        multiple
        onChange={(_, data) => {
          setIsError(false);
          setSelectedGroups(data);
        }}
        value={selectedGroups}
        options={multiUserGroups?.filter((g) => g.id !== groupID)}
        getOptionLabel={(group) => group.name}
        filterSelectedOptions
        renderInput={(field) => (
          <TextField
            {...field}
            error={isError}
            helperText={isError ? "Select at least one group" : ""}
            label="Group of users to add"
            data-testid="addUsersFromGroupsTextField"
          />
        )}
      />
      <Button primary name="submitAddFromGroupsButton" onClick={handleSubmit}>
        Add group of users
      </Button>
    </Box>
  );
};
AddGroupOfUsersForm.propTypes = {
  groupID: PropTypes.number.isRequired,
};

export default AddGroupOfUsersForm;

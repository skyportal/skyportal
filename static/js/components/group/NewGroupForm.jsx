import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { useTheme } from "@mui/material/styles";
import Select from "@mui/material/Select";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

import * as groupsActions from "../../ducks/groups";
import * as usersActions from "../../ducks/users";
import Button from "../Button";
import Paper from "../Paper";

const NewGroupForm = () => {
  const theme = useTheme();
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);

  const [formState, setState] = useState({
    name: "",
    nickname: "",
    description: "",
    group_admins: [],
  });

  useEffect(() => {
    if (!allUsers.length) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const userIDToName = {};
  allUsers?.forEach((u) => {
    userIDToName[u.id] = u.username;
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    const result = await dispatch(groupsActions.addNewGroup(formState));
    if (result.status === "success") {
      dispatch(groupsActions.fetchGroups(true));
      setState({
        name: "",
        nickname: "",
        description: "",
        group_admins: [],
      });
    }
  };

  const handleChange = (event) => {
    const newState = {};
    newState[event.target.name] = event.target.value;
    setState({
      ...formState,
      ...newState,
    });
  };

  return (
    <Paper sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Typography variant="h6">Create New Group</Typography>
      <TextField
        label="Group Name"
        name="name"
        value={formState.name}
        onChange={handleChange}
        sx={{ width: { xs: "100%", sm: "50%" } }}
      />
      <TextField
        label="Nickname"
        name="nickname"
        value={formState.nickname}
        onChange={handleChange}
        sx={{ width: { xs: "100%", sm: "50%" } }}
      />
      <TextField
        label="Description"
        name="description"
        value={formState.description}
        onChange={handleChange}
        sx={{ width: { xs: "100%", sm: "50%" } }}
      />
      <FormControl
        id="select-admins-label"
        sx={{ width: { xs: "100%", sm: "50%" } }}
      >
        <InputLabel>Group Admins</InputLabel>
        <Select
          labelId="select-admins-label"
          label="Group Admins"
          id="groupAdminsSelect"
          name="group_admins"
          multiple
          onChange={handleChange}
          renderValue={(selected) => (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {selected.map((value) => (
                <Chip
                  key={value}
                  label={userIDToName[value]}
                  sx={{ margin: "0.1rem" }}
                />
              ))}
            </Box>
          )}
          defaultValue={[]}
        >
          {allUsers.map((user) => (
            <MenuItem
              key={user.id}
              value={user.id}
              sx={{
                fontWeight: formState.group_admins.includes(user.id)
                  ? theme.typography.fontWeightMedium
                  : theme.typography.fontWeightRegular,
              }}
            >
              {user.username}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Box>
        <Button primary onClick={handleSubmit}>
          Create Group
        </Button>
      </Box>
    </Paper>
  );
};

export default NewGroupForm;

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Box from "@mui/material/Box";
import Select from "@mui/material/Select";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Input from "@mui/material/Input";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import TextField from "@mui/material/TextField";
import Paper from "@mui/material/Paper";
import { useTheme } from "@mui/material/styles";

import makeStyles from "@mui/styles/makeStyles";

import * as groupsActions from "../../ducks/groups";
import * as usersActions from "../../ducks/users";
import Button from "../Button";

const getStyles = (userID, userIDs = [], theme) => ({
  fontWeight:
    userIDs.indexOf(userID) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const NewGroupForm = () => {
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);

  const [formState, setState] = useState({
    name: "",
    nickname: "",
    description: "",
    group_admins: [],
  });

  useEffect(() => {
    if (allUsers.length === 0) {
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

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: `${theme.spacing(1)} 0`,
      minWidth: "50%",
    },
    customTextField: {
      width: "50%", // Set the desired width
      marginBottom: theme.spacing(2), // Example spacing
    },
    chips: {
      display: "flex",
      flexWrap: "wrap",
    },
    chip: {
      margin: 2,
    },
    newGroupForm: {
      position: "relative",
    },
    container: {
      padding: "1rem",
      margin: "1rem 0",
    },
  }));
  const classes = useStyles();
  const theme = useTheme();
  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };

  return (
    <Paper className={classes.container}>
      <h3>Create New Group</h3>
      <form className={classes.newGroupForm} onSubmit={handleSubmit}>
        <Box>
          <TextField
            label="Group Name"
            name="name"
            value={formState.name}
            onChange={handleChange}
            className={classes.customTextField}
          />
        </Box>
        <Box>
          <TextField
            label="Nickname"
            name="nickname"
            value={formState.nickname}
            onChange={handleChange}
            className={classes.customTextField}
          />
        </Box>
        <Box>
          <TextField
            label="Description"
            name="description"
            value={formState.description}
            onChange={handleChange}
            className={classes.customTextField}
          />
        </Box>
        <Box>
          <FormControl className={classes.formControl}>
            <InputLabel id="select-admins-label">Group Admins</InputLabel>
            <Select
              labelId="select-admins-label"
              id="groupAdminsSelect"
              name="group_admins"
              multiple
              onChange={handleChange}
              input={<Input id="selectAdminsChip" />}
              renderValue={(selected) => (
                <div className={classes.chips}>
                  {selected.map((value) => (
                    <Chip
                      key={value}
                      label={userIDToName[value]}
                      className={classes.chip}
                    />
                  ))}
                </div>
              )}
              MenuProps={MenuProps}
              defaultValue={[]}
            >
              {allUsers.map((user) => (
                <MenuItem
                  key={user.id}
                  value={user.id}
                  style={getStyles(user.id, formState.group_admins, theme)}
                >
                  {user.username}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        <Box>
          <Button primary type="submit">
            Create Group
          </Button>
        </Box>
      </form>
    </Paper>
  );
};

export default NewGroupForm;

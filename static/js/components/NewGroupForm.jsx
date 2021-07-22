import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";

import Box from "@material-ui/core/Box";
import Button from "@material-ui/core/Button";
import Select from "@material-ui/core/Select";
import Chip from "@material-ui/core/Chip";
import MenuItem from "@material-ui/core/MenuItem";
import Input from "@material-ui/core/Input";
import FormControl from "@material-ui/core/FormControl";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from "@material-ui/core/TextField";
import { makeStyles, useTheme } from "@material-ui/core/styles";

import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";
import styles from "./NewGroupForm.css";

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
    group_admins: [],
  });

  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(usersActions.fetchUsers());
    }
  }, [dispatch, allUsers]);

  const userIDToName = {};
  allUsers.forEach((u) => {
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
      margin: `${theme.spacing(1)}px 0`,
      minWidth: 130,
    },
    chips: {
      display: "flex",
      flexWrap: "wrap",
    },
    chip: {
      margin: 2,
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
    <Box p={2}>
      <h3>Create New Group</h3>
      <form className={styles.newGroupForm} onSubmit={handleSubmit}>
        <Box>
          <TextField
            label="Group Name"
            name="name"
            value={formState.name}
            onChange={handleChange}
          />
        </Box>
        <Box>
          <TextField
            label="Nickname"
            name="nickname"
            value={formState.nickname}
            onChange={handleChange}
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
          <Button type="submit" variant="contained" color="primary">
            Create Group
          </Button>
        </Box>
      </form>
    </Box>
  );
};

export default NewGroupForm;

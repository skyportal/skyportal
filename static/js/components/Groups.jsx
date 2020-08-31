import React from "react";
import { useSelector } from "react-redux";

import Paper from "@material-ui/core/Paper";
import { makeStyles } from "@material-ui/core/styles";

import GroupManagement from "./GroupManagement";
import GroupList from "./GroupList";

const useStyles = makeStyles((theme) => ({
  paper: {
    width: "100%",
    padding: theme.spacing(1),
    textAlign: "left",
    color: theme.palette.text.primary,
  },
}));

const Groups = () => {
  const roles = useSelector((state) => state.profile.roles);
  const groups = useSelector((state) => state.groups.user);

  const classes = useStyles();

  return (
    <div>
      <Paper className={classes.paper}>
        <GroupList title="My Groups" groups={groups} />
      </Paper>
      <br />
      {roles.includes("Super admin") && <GroupManagement />}
    </div>
  );
};

export default Groups;

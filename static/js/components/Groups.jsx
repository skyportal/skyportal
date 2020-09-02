import React from "react";
import { useSelector } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";

import GroupManagement from "./GroupManagement";
import GroupList from "./GroupList";

const useStyles = makeStyles(() => ({
  // Hide drag handle icon since this isn't the home page
  widgetIcon: {
    display: "none",
  },
  widgetPaperDiv: {
    padding: "1rem",
    height: "100%",
  },
}));

const Groups = () => {
  const classes = useStyles();
  const roles = useSelector((state) => state.profile.roles);
  const groups = useSelector((state) => state.groups.user);

  return (
    <div>
      <GroupList title="My Groups" groups={groups} classes={classes} />
      <br />
      {roles.includes("Super admin") && <GroupManagement />}
    </div>
  );
};

export default Groups;

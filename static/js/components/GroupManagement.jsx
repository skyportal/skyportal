import React from "react";
import { useSelector } from "react-redux";

import Paper from "@material-ui/core/Paper";
import Box from "@material-ui/core/Box";
import Typography from "@material-ui/core/Typography";
import { makeStyles } from "@material-ui/core/styles";

import NewGroupForm from "./NewGroupForm";
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
  widgetPaperFillSpace: {
    height: "100%",
  },
}));

const GroupManagement = () => {
  const classes = useStyles();
  const allGroups = useSelector((state) => state.groups.all).filter(
    (group) => !group.single_user_group
  );

  return (
    <Paper variant="outlined">
      <Box p={1}>
        <Typography variant="h5">Group Management</Typography>
        <NewGroupForm />
        <GroupList title="All Groups" groups={allGroups} classes={classes} />
      </Box>
    </Paper>
  );
};

export default GroupManagement;

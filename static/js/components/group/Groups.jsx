import React from "react";
import { useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Box from "@mui/material/Box";

import Spinner from "../Spinner";
import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import NonMemberGroupList from "./NonMemberGroupList";

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
  const { permissions } = useSelector((state) => state.profile);
  const { user: userGroups, all: allGroups } = useSelector(
    (state) => state.groups,
  );
  const allRealGroups = allGroups?.filter((group) => !group.single_user_group);

  if (userGroups.length === 0 || allGroups === null) return <Spinner />;

  const nonMemberGroups = allGroups?.filter(
    (g) =>
      !g.single_user_group && !userGroups.map((ug) => ug.id).includes(g.id),
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <GroupList title="My Groups" groups={userGroups} classes={classes} />
      {!!nonMemberGroups.length && (
        <NonMemberGroupList groups={nonMemberGroups} />
      )}
      <NewGroupForm />
      {permissions.includes("System admin") && (
        <GroupList
          title="All Groups"
          groups={allRealGroups}
          classes={classes}
        />
      )}
    </Box>
  );
};

export default Groups;

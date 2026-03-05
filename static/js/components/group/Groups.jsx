import React from "react";
import { useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Box from "@mui/material/Box";

import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import NonMemberGroupList from "./NonMemberGroupList";
import Spinner from "../Spinner";

const useStyles = makeStyles(() => ({
  // Hide drag handle icon since this isn't the home page
  widgetIcon: { display: "none" },
}));

const Groups = () => {
  const classes = useStyles();
  const { permissions } = useSelector((state) => state.profile);
  const { user: userGroups, all: allGroups } = useSelector(
    (state) => state.groups,
  );

  if (!userGroups.length || !allGroups) return <Spinner />;

  const canManageGroups = permissions.includes("System admin");
  const allMultiUserGroups = allGroups.filter((g) => !g.single_user_group);
  const nonMemberGroups = allMultiUserGroups?.filter(
    (g) => !userGroups.map((ug) => ug.id).includes(g.id),
  );

  return (
    <Box display="flex" flexDirection="column" gap="1rem">
      <GroupList
        title="My Groups"
        groups={userGroups}
        classes={classes}
        listMaxHeight="65vh"
      />
      {!!nonMemberGroups.length && (
        <NonMemberGroupList groups={nonMemberGroups} />
      )}
      <NewGroupForm />
      {canManageGroups && (
        <GroupList
          title="All Groups"
          groups={allMultiUserGroups}
          classes={classes}
        />
      )}
    </Box>
  );
};

export default Groups;

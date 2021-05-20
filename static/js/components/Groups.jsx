import React from "react";
import { useSelector } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";

import GroupManagement from "./GroupManagement";
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
  widgetPaperFillSpace: {
    height: "100%",
  },
}));

const Groups = () => {
  const classes = useStyles();
  const { permissions } = useSelector((state) => state.profile);
  const { user: userGroups, all: allGroups } = useSelector(
    (state) => state.groups
  );

  if (userGroups.length === 0 || allGroups === null) {
    return <h3>Loading...</h3>;
  }

  const nonMemberGroups = allGroups.filter(
    (g) => !g.single_user_group && !userGroups.map((ug) => ug.id).includes(g.id)
  );

  return (
    <div>
      <GroupList title="My Groups" groups={userGroups} classes={classes} />
      {!!nonMemberGroups.length && (
        <>
          <br />
          <NonMemberGroupList groups={nonMemberGroups} />
        </>
      )}
      <NewGroupForm />
      {permissions.includes("System admin") && <GroupManagement />}
    </div>
  );
};

export default Groups;

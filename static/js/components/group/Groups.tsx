import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";

import { useGetGroupsQuery } from "../../ducks/groups";
import { useAppSelector } from "../../types/hooks";
import GroupManagement from "./GroupManagement";
import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import NonMemberGroupList from "./NonMemberGroupList";

const useStyles = makeStyles()(() => ({
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
  const { classes } = useStyles();
  const { permissions } = useAppSelector((state) => state.profile);
  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = groupsData?.user ?? [];
  const allGroups = groupsData?.all ?? null;

  if (userGroups.length === 0 || allGroups === null) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const nonMemberGroups = allGroups?.filter(
    (g) =>
      !g["single_user_group"] && !userGroups.map((ug) => ug.id).includes(g.id),
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

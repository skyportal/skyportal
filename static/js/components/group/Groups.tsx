import { useGetProfileQuery } from "../../ducks/profile";
import { makeStyles } from "tss-react/mui";
import Box from "@mui/material/Box";

import { useGetGroupsQuery } from "../../ducks/groups";
import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import NonMemberGroupList from "./NonMemberGroupList";
import Spinner from "../Spinner";

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
  const { permissions } = useGetProfileQuery().data ?? {};
  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = groupsData?.user ?? [];
  const allGroups = groupsData?.all ?? null;

  if (!userGroups.length || allGroups === null) return <Spinner />;

  const canManageGroups = permissions?.includes("System admin");
  const allMultiUserGroups = allGroups.filter((g) => !g["single_user_group"]);
  const nonMemberGroups = allMultiUserGroups?.filter(
    (g) => !userGroups.map((ug) => ug.id).includes(g.id),
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div data-testid="tour-groups-list">
        <GroupList
          title="My Groups"
          groups={userGroups}
          classes={classes}
          listMaxHeight="65vh"
        />
      </div>
      {!!nonMemberGroups.length && (
        <div data-testid="tour-groups-request">
          <NonMemberGroupList groups={nonMemberGroups} />
        </div>
      )}
      <div data-testid="tour-groups-new">
        <NewGroupForm />
      </div>
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

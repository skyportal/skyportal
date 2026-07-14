import { useState } from "react";
import { useGetProfileQuery } from "../../ducks/profile";
import { makeStyles } from "tss-react/mui";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

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

  const [tab, setTab] = useState(0);

  if (!userGroups.length || allGroups === null) return <Spinner />;

  const canManageGroups = permissions?.includes("System admin");
  const allMultiUserGroups = allGroups.filter((g) => !g["single_user_group"]);
  const nonMemberGroups = allMultiUserGroups?.filter(
    (g) => !userGroups.map((ug) => ug.id).includes(g.id),
  );

  const tabPanels = [
    <GroupList
      key="my-groups"
      title="My Groups"
      groups={userGroups}
      classes={classes}
      listMaxHeight="65vh"
    />,
    ...(nonMemberGroups.length
      ? [<NonMemberGroupList key="non-member" groups={nonMemberGroups} />]
      : []),
    <NewGroupForm key="new-group" />,
    ...(canManageGroups
      ? [
          <GroupList
            key="all-groups"
            title="All Groups"
            groups={allMultiUserGroups}
            classes={classes}
          />,
        ]
      : []),
  ];

  const activeTab = Math.min(tab, tabPanels.length - 1);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs value={activeTab} onChange={(_event, value) => setTab(value)}>
          <Tab label="My Groups" data-testid="tour-groups-list" />
          {nonMemberGroups.length > 0 && (
            <Tab label="Non-member groups" data-testid="tour-groups-request" />
          )}
          <Tab label="Create New Group" data-testid="tour-groups-new" />
          {canManageGroups && <Tab label="All Groups" />}
        </Tabs>
      </Box>
      {tabPanels[activeTab]}
    </Box>
  );
};

export default Groups;

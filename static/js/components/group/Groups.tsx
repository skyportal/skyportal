import { useState } from "react";
import { useGetProfileQuery } from "../../ducks/profile";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import { useGetGroupsQuery } from "../../ducks/groups";
import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import Spinner from "../Spinner";

const Groups = () => {
  const { permissions } = useGetProfileQuery().data ?? {};
  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = groupsData?.user ?? [];
  const allGroups = groupsData?.all ?? null;

  const [tab, setTab] = useState(0);
  // Shared across tabs so a search typed in one list survives switching
  // tabs; it only resets when this component unmounts (i.e. leaving the page).
  const [filterModel, setFilterModel] = useState({
    items: [],
    quickFilterValues: [],
  });

  if (!userGroups.length || allGroups === null) return <Spinner />;

  const canManageGroups = permissions?.includes("System admin");
  const allMultiUserGroups = allGroups.filter((g) => !g["single_user_group"]);
  const nonMemberGroups = allMultiUserGroups?.filter(
    (g) => !userGroups.map((ug) => ug.id).includes(g.id),
  );

  const tabPanels = [
    <GroupList
      key="my-groups"
      title="My groups"
      groups={userGroups}
      filterModel={filterModel}
      onFilterModelChange={setFilterModel}
    />,
    ...(nonMemberGroups.length
      ? [
          <GroupList
            key="non-member"
            title="Non-member groups"
            groups={nonMemberGroups}
            admission
            filterModel={filterModel}
            onFilterModelChange={setFilterModel}
          />,
        ]
      : []),
    ...(canManageGroups
      ? [
          <GroupList
            key="all-groups"
            title="All Groups"
            groups={allMultiUserGroups}
            filterModel={filterModel}
            onFilterModelChange={setFilterModel}
          />,
        ]
      : []),
    <Box key="new-group" sx={{ borderTop: 1, borderColor: "divider" }}>
      <NewGroupForm />
    </Box>,
  ];

  const activeTab = Math.min(tab, tabPanels.length - 1);

  return (
    <Box>
      <Tabs
        value={activeTab}
        onChange={(_event, value) => setTab(value)}
        centered
      >
        <Tab label="My Groups" data-testid="tour-groups-list" />
        {nonMemberGroups.length > 0 && (
          <Tab label="Non-member groups" data-testid="tour-groups-request" />
        )}
        {canManageGroups && <Tab label="All Groups" />}
        <Tab label="Create New Group" data-testid="tour-groups-new" />
      </Tabs>
      {tabPanels[activeTab]}
    </Box>
  );
};

export default Groups;

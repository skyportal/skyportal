import { useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import Spinner from "../Spinner";

const Groups = () => {
  const { permissions } = useGetProfileQuery().data ?? {};
  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = groupsData?.user ?? [];
  const allGroups = groupsData?.all ?? null;
  const [view, setView] = useState("my");
  const [newGroupOpen, setNewGroupOpen] = useState(false);

  if (!userGroups.length || allGroups === null) return <Spinner />;

  const allMultiUserGroups = allGroups.filter((g) => !g["single_user_group"]);
  const userGroupIds = userGroups.map((g) => g.id);
  const views = [
    { value: "my", label: "My Groups", groups: userGroups },
    {
      value: "non-member",
      label: "Non-member groups",
      groups: allMultiUserGroups.filter((g) => !userGroupIds.includes(g.id)),
    },
    ...(permissions?.includes("System admin")
      ? [{ value: "all", label: "All Groups", groups: allMultiUserGroups }]
      : []),
  ].filter((v) => v.value === "my" || v.groups.length > 0);
  const current = views.find((v) => v.value === view) ?? views[0]!;

  return (
    <>
      <GroupList
        title="Groups"
        groups={current.groups}
        admission={current.value === "non-member"}
      >
        <TextField
          select
          size="small"
          value={current.value}
          onChange={(e) => setView(e.target.value)}
          data-testid="groupsViewSelect"
          sx={{ minWidth: 190 }}
        >
          {views.map((v) => (
            <MenuItem key={v.value} value={v.value}>
              {v.label}
            </MenuItem>
          ))}
        </TextField>
        <Tooltip title="Create new group">
          <IconButton
            onClick={() => setNewGroupOpen(true)}
            data-testid="tour-groups-new"
          >
            <AddIcon />
          </IconButton>
        </Tooltip>
      </GroupList>
      <Dialog
        open={newGroupOpen}
        onClose={() => setNewGroupOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogContent>
          <NewGroupForm onCreated={() => setNewGroupOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default Groups;

import { useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";

import { useGetGroupsQuery } from "../../ducks/groups";
import GroupList from "./GroupList";
import NewGroupForm from "./NewGroupForm";
import Spinner from "../Spinner";

const Groups = () => {
  const { data: groupsData } = useGetGroupsQuery();
  const userGroups = groupsData?.user ?? [];
  const allGroups = groupsData?.all ?? null;
  const [showAll, setShowAll] = useState(false);
  const [newGroupOpen, setNewGroupOpen] = useState(false);

  if (!userGroups.length || allGroups === null) return <Spinner />;

  return (
    <>
      <GroupList
        title="Groups"
        groups={showAll ? allGroups : userGroups}
        memberGroupIds={userGroups.map((g) => g.id)}
      >
        <FormControlLabel
          label="Show all groups"
          data-testid="showAllGroupsSwitch"
          control={
            <Switch
              size="small"
              checked={showAll}
              onChange={(e) => setShowAll(e.target.checked)}
            />
          }
        />
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

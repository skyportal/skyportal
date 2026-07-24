import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTheme } from "@mui/material/styles";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

import CircularProgress from "@mui/material/CircularProgress";
import Button from "../Button";

import GroupUsers from "./GroupUsers";
import GroupFiltersStreams from "./GroupFiltersStreams";
import GroupSources from "./GroupSources";
import GroupSettingsForm from "./GroupSettingsForm";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupQuery } from "../../ducks/group";
import { useDeleteGroupMutation } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const Group = () => {
  const [deleteGroup] = useDeleteGroupMutation();
  const theme = useTheme();
  const navigate = useNavigate();

  const [groupLoadError, setGroupLoadError] = useState("");

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [tab, setTab] = useState(0);

  const handleConfirmDeleteDialogClose = () => {
    setConfirmDeleteOpen(false);
  };

  const { id } = useParams();

  const { data: group, error: groupError } = useGetGroupQuery(id as string, {
    skip: !id,
  });
  const { data: currentUser } = useGetProfileQuery();
  const { error: streamsError } = useGetStreamsQuery();

  useEffect(() => {
    if (groupError) {
      setGroupLoadError((groupError as any)?.error ?? "Failed to load group");
    }
  }, [groupError]);

  useEffect(() => {
    if (streamsError) {
      setGroupLoadError(
        (streamsError as any)?.error ?? "Failed to load streams",
      );
    }
  }, [streamsError]);

  const handleDeleteGroup = async () => {
    try {
      await deleteGroup(group?.["id"] as number).unwrap();
      setConfirmDeleteOpen(false);
      navigate("/groups");
    } catch {
      // error notification handled by the API layer
    }
  };

  if (groupLoadError) return groupLoadError;

  if (group == null) return <CircularProgress />;

  const isAdmin = (aUser: any) => {
    const currentGroupUser = group?.["users"]?.filter(
      (group_user: any) => group_user.id === aUser.id,
    )[0];
    return (
      (currentGroupUser && (currentGroupUser as any)?.["admin"]) ||
      aUser.permissions?.includes("System admin") ||
      aUser.permissions?.includes("Manage groups")
    );
  };

  return (
    <div>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
        }}
      >
        <Box>
          <Typography variant="h5">
            <b>Group: </b>
            {group["name"]}
            {group["nickname"] ? ` (${group["nickname"]})` : ""}
          </Typography>
          {group["description"] && (
            <Typography sx={{ padding: 0.5 }} data-testid="description">
              {group["description"]}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {isAdmin(currentUser) && <GroupSettingsForm group={group} />}
          {isAdmin(currentUser) && (
            <Button
              variant="outlined"
              color="error"
              onClick={() => setConfirmDeleteOpen(true)}
              sx={{ marginRight: 2 }}
            >
              Delete Group
            </Button>
          )}
        </Box>
      </Box>
      <Box sx={{ borderBottom: 1, borderColor: "divider", mt: 2 }}>
        <Tabs value={tab} onChange={(_event, value) => setTab(value)}>
          <Tab label="Members" data-testid="tour-group-members" />
          <Tab label="Sources" />
          <Tab label="Streams and filters" data-testid="tour-group-filters" />
        </Tabs>
      </Box>
      {tab === 0 && (
        <GroupUsers
          group={group}
          currentUser={currentUser as any}
          theme={theme}
          isAdmin={isAdmin}
        />
      )}
      {/* key: this stays mounted across group -> group navigation, so remount to
          reset the queries and table state onto the new group. */}
      {tab === 1 && <GroupSources key={id} route={{ id: id as string }} />}
      {tab === 2 && (
        <GroupFiltersStreams
          group={group}
          currentUser={currentUser}
          isAdmin={isAdmin}
          theme={theme}
        />
      )}
      <Dialog
        fullWidth
        open={confirmDeleteOpen}
        onClose={handleConfirmDeleteDialogClose}
      >
        <DialogTitle>Delete Group?</DialogTitle>
        <DialogContent dividers>
          <DialogContentText>
            Are you sure you want to delete this Group?
            <br />
            <Typography variant="caption" color="warning.dark">
              (This will delete the group and all of its filters. All source
              data will be transferred to the Sitewide group.)
            </Typography>
          </DialogContentText>
        </DialogContent>

        <DialogActions>
          <Button
            secondary
            autoFocus
            onClick={() => setConfirmDeleteOpen(false)}
          >
            Dismiss
          </Button>
          <Button primary onClick={handleDeleteGroup}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default Group;

import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
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

import Button from "../Button";
import Spinner from "../Spinner";

import GroupUsers from "./GroupUsers";
import GroupFiltersStreams from "./GroupFiltersStreams";
import GroupSources from "./GroupSources";
import GroupSettingsForm from "./GroupSettingsForm";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupQuery } from "../../ducks/group";
import { useDeleteGroupMutation } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const Group = () => {
  const [deleteGroup, { isLoading: isDeleting, isSuccess: isDeleted }] =
    useDeleteGroupMutation();
  const theme = useTheme();
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(searchParams.get("tab") === "filters" ? 2 : 0);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const { data: group, error: groupError } = useGetGroupQuery(id as string, {
    skip: !id || isDeleting || isDeleted,
  });
  const { data: currentUser } = useGetProfileQuery();
  const { error: streamsError } = useGetStreamsQuery();

  if (groupError) return (groupError as any)?.error ?? "Failed to load group";
  if (streamsError)
    return (streamsError as any)?.error ?? "Failed to load streams";
  if (group == null || currentUser == null) return <Spinner />;

  const handleDeleteGroup = async () => {
    const { error } = await deleteGroup(group["id"] as number);
    if (!error) navigate("/groups");
  };

  const isAdmin = (aUser: any) =>
    group["users"]?.some((u: any) => u.id === aUser.id && u.admin) ||
    aUser.permissions?.includes("System admin") ||
    aUser.permissions?.includes("Manage groups");

  return (
    <Box>
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
        {isAdmin(currentUser) && (
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <GroupSettingsForm group={group} />
            <Button
              variant="outlined"
              color="error"
              onClick={() => setConfirmDeleteOpen(true)}
              sx={{ marginRight: 2 }}
            >
              Delete Group
            </Button>
          </Box>
        )}
      </Box>
      <Tabs
        sx={{ borderBottom: 1, borderColor: "divider" }}
        value={tab}
        onChange={(_event, value) => setTab(value)}
      >
        <Tab label="Members" data-testid="tour-group-members" />
        <Tab label="Sources" />
        <Tab label="Streams and filters" data-testid="tour-group-filters" />
      </Tabs>
      {tab === 0 && (
        <GroupUsers
          group={group}
          currentUser={currentUser as any}
          theme={theme}
          isAdmin={isAdmin}
        />
      )}
      {/* key: remounts on group -> group navigation to reset queries and table state */}
      {tab === 1 && <GroupSources key={id} route={{ id: id as string }} />}
      {tab === 2 && (
        <GroupFiltersStreams
          group={group}
          currentUser={currentUser}
          isAdmin={isAdmin}
        />
      )}
      <Dialog
        fullWidth
        open={confirmDeleteOpen}
        onClose={() => setConfirmDeleteOpen(false)}
      >
        <DialogTitle>Delete Group?</DialogTitle>
        <DialogContent dividers>
          <DialogContentText>
            Are you sure you want to delete this Group?
            <Typography
              variant="caption"
              color="warning.dark"
              sx={{ display: "block" }}
            >
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
    </Box>
  );
};

export default Group;

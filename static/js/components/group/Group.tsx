import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import useTabParam from "../../hooks/useTabParam";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import DeleteIcon from "@mui/icons-material/Delete";
import LogoutIcon from "@mui/icons-material/Logout";

import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import Spinner from "../Spinner";
import { FULL_PAGE_HEIGHT } from "../StyledDataGrid";

import GroupUsers from "./GroupUsers";
import GroupAddMembers from "./GroupAddMembers";
import GroupAdmissionRequestsManagement from "./GroupAdmissionRequestsManagement";
import GroupFiltersStreams from "./GroupFiltersStreams";
import GroupSources from "./GroupSources";
import GroupSettingsForm from "./GroupSettingsForm";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupQuery } from "../../ducks/group";
import {
  useDeleteGroupMutation,
  useDeleteGroupUserMutation,
} from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const Group = () => {
  const [deleteGroup, { isLoading: isDeleting, isSuccess: isDeleted }] =
    useDeleteGroupMutation();
  const [deleteGroupUser, { isLoading: isLeaving, isSuccess: hasLeft }] =
    useDeleteGroupUserMutation();
  const navigate = useNavigate();
  const { id } = useParams();
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [confirmLeaveOpen, setConfirmLeaveOpen] = useState(false);

  const { data: group, error: groupError } = useGetGroupQuery(id as string, {
    skip: !id || isDeleting || isDeleted || isLeaving || hasLeft,
  });
  const { data: currentUser } = useGetProfileQuery();
  const { error: streamsError } = useGetStreamsQuery();

  const isAdmin = (aUser: any) =>
    group?.["users"]?.some((u: any) => u.id === aUser.id && u.admin) ||
    aUser.permissions?.includes("System admin") ||
    aUser.permissions?.includes("Manage groups");
  const canManage = currentUser != null && isAdmin(currentUser);
  const tabNames = canManage
    ? ["members", "admissions", "sources", "filters"]
    : ["members", "sources", "filters"];
  const [tab, setTab] = useTabParam(tabNames);
  const tabName = tabNames[tab];

  if (groupError) return (groupError as any)?.error ?? "Failed to load group";
  if (streamsError)
    return (streamsError as any)?.error ?? "Failed to load streams";
  if (group == null || currentUser == null) return <Spinner />;

  const groupID = group["id"] as number;

  const handleDeleteGroup = async () => {
    const { error } = await deleteGroup(groupID);
    if (!error) navigate("/groups");
  };

  const groupUsers: any[] = group["users"] ?? [];
  const membership = groupUsers.find((u) => u.id === currentUser.id);
  const canLeave = membership != null && !group["single_user_group"];
  const isLastAdmin =
    membership?.admin && groupUsers.filter((u) => u.admin).length === 1;

  const handleLeaveGroup = async () => {
    setConfirmLeaveOpen(false);
    const { error } = await deleteGroupUser({
      userID: currentUser.id,
      group_id: groupID,
    });
    if (!error) navigate("/groups");
  };

  return (
    <Box
      sx={
        tabName === "members"
          ? {
              height: FULL_PAGE_HEIGHT,
              display: "flex",
              flexDirection: "column",
            }
          : {}
      }
    >
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
        {(canManage || canLeave) && (
          <Box sx={{ display: "flex", gap: 0.5, mr: 1 }}>
            {canManage && (
              <>
                <GroupAddMembers groupID={groupID} />
                <GroupSettingsForm group={group} />
              </>
            )}
            {canLeave && (
              <Tooltip
                title={
                  isLastAdmin
                    ? "Make another member admin before leaving"
                    : "Leave group"
                }
              >
                <span>
                  <IconButton
                    onClick={() => setConfirmLeaveOpen(true)}
                    disabled={isLastAdmin}
                    data-testid="leaveGroupButton"
                  >
                    <LogoutIcon />
                  </IconButton>
                </span>
              </Tooltip>
            )}
            {canManage && (
              <Tooltip title="Delete group">
                <IconButton
                  color="error"
                  onClick={() => setConfirmDeleteOpen(true)}
                  data-testid="deleteGroupButton"
                >
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        )}
      </Box>
      <Tabs
        sx={{ borderBottom: 1, borderColor: "divider" }}
        value={tab}
        onChange={(_event, value) => setTab(value)}
      >
        <Tab label="Members" data-testid="tour-group-members" />
        {canManage && <Tab label="Admissions" />}
        <Tab label="Sources" />
        <Tab label="Streams and filters" data-testid="tour-group-filters" />
      </Tabs>
      {tabName === "members" && (
        <GroupUsers group={group} currentUser={currentUser} isAdmin={isAdmin} />
      )}
      {tabName === "admissions" && (
        <Box sx={{ p: 1.5 }}>
          <GroupAdmissionRequestsManagement groupID={groupID} />
        </Box>
      )}
      {/* key: remounts on group -> group navigation to reset queries and table state */}
      {tabName === "sources" && (
        <GroupSources key={id} route={{ id: id as string }} />
      )}
      {tabName === "filters" && (
        <GroupFiltersStreams
          group={group}
          currentUser={currentUser}
          isAdmin={isAdmin}
        />
      )}
      <ConfirmDeletionDialog
        deleteFunction={handleDeleteGroup}
        dialogOpen={confirmDeleteOpen}
        closeDialog={() => setConfirmDeleteOpen(false)}
        resourceName="Group"
        message={
          <>
            Are you sure you want to delete this Group?
            <Typography
              variant="caption"
              color="warning.dark"
              sx={{ display: "block" }}
            >
              (This will delete the group and all of its filters. All source
              data will be transferred to the Sitewide group.)
            </Typography>
          </>
        }
      />
      <ConfirmDeletionDialog
        deleteFunction={handleLeaveGroup}
        dialogOpen={confirmLeaveOpen}
        closeDialog={() => setConfirmLeaveOpen(false)}
        resourceName="membership"
        title="Leave group?"
        message="You will lose access to this group's sources and filters."
      />
    </Box>
  );
};

export default Group;

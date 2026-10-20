import { useState } from "react";

import { useNavigate } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import { useAppDispatch } from "../../types/hooks";
import { groupApi } from "../../ducks/group";
import {
  useDeleteGroupUserMutation,
  useUpdateGroupUserMutation,
} from "../../ducks/groups";
import { Box } from "@mui/material";

interface ManageUserButtonsProps {
  loadedId: number;
  user: {
    id: number;
    username: string;
    [key: string]: any;
  };
  isAdmin: (...args: any[]) => any;
  group: {
    id: number;
    users?: { admin: boolean; [key: string]: any }[];
    [key: string]: any;
  };
  currentUser: {
    id: number;
    username: string;
    [key: string]: any;
  };
}

const ManageUserButtons = ({
  group,
  loadedId,
  user,
  isAdmin,
  currentUser,
}: ManageUserButtonsProps) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [updateGroupUser] = useUpdateGroupUserMutation();
  const [deleteGroupUser] = useDeleteGroupUserMutation();

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const handleConfirmDeleteDialogClose = () => {
    setConfirmDeleteOpen(false);
  };

  if (!isAdmin(currentUser) && user.username !== currentUser.username)
    return null;

  let numAdmins = 0;
  group?.users?.forEach((groupUser) => {
    if (groupUser?.admin) {
      numAdmins += 1;
    }
  });

  const groupUser = group?.users?.find((u) => u["id"] === user.id);
  const permissions = [
    {
      param: "admin",
      label: "Admin",
      name: "admin status",
      granted: Boolean(isAdmin(user)),
      disabled: isAdmin(user) && numAdmins === 1,
    },
    {
      param: "canSave",
      label: "Save",
      name: "save access",
      granted: Boolean(groupUser?.["can_save"]),
      disabled: false,
    },
    {
      param: "canSharePhotometry",
      label: "Share photometry",
      name: "photometry sharing",
      granted: Boolean(groupUser?.["can_share_photometry"]),
      disabled: false,
    },
  ];

  const togglePermission = async (
    param: string,
    granted: boolean,
    name: string,
  ) => {
    const { error } = await updateGroupUser({
      groupID: loadedId,
      params: { userID: user.id, [param]: !granted },
    });
    if (error) return;
    dispatch(showNotification(`User ${name} for this group updated.`));
    dispatch(groupApi.util.invalidateTags([{ type: "Group", id: loadedId }]));
  };

  const handleDelete = () => {
    if (user.username === currentUser.username) navigate("/groups");
    deleteGroupUser({
      userID: user.id,
      group_id: group.id,
    });
  };

  return (
    <Box
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}
    >
      {isAdmin(currentUser) &&
        permissions.map(({ param, label, name, granted, disabled }) => (
          <Tooltip
            key={param}
            title={`${granted ? "Revoke" : "Grant"} ${name}`}
          >
            <span>
              <Chip
                size="small"
                label={label}
                color={granted ? "primary" : "default"}
                variant={granted ? "filled" : "outlined"}
                disabled={disabled}
                onClick={() => togglePermission(param, granted, name)}
                data-testid={`${param}-${user.username}`}
              />
            </span>
          </Tooltip>
        ))}
      <IconButton
        size="small"
        data-testid={`delete-${user.username}`}
        onClick={() => setConfirmDeleteOpen(true)}
        disabled={isAdmin(user) && numAdmins === 1}
        color="error"
      >
        <DeleteIcon fontSize="small" />
      </IconButton>
      <Dialog
        fullWidth
        open={confirmDeleteOpen}
        onClose={handleConfirmDeleteDialogClose}
      >
        {user.username === currentUser.username ? (
          <>
            <DialogTitle>Remove yourself?</DialogTitle>
            <DialogContent dividers>
              <DialogContentText>
                Are you sure you want to delete yourself from this group?
                <br />
                <Typography variant="caption" color="warning.dark">
                  (This will delete you from the group and all of its filters.)
                </Typography>
              </DialogContentText>
            </DialogContent>
          </>
        ) : (
          <>
            <DialogTitle>Remove user?</DialogTitle>
            <DialogContent dividers>
              <DialogContentText>
                Are you sure you want to delete this user from this group?
                <br />
                <Typography variant="caption" color="warning.dark">
                  (This will delete the user from this group and all of its
                  filters.)
                </Typography>
              </DialogContentText>
            </DialogContent>
          </>
        )}

        <DialogActions>
          <Button
            secondary
            autoFocus
            onClick={() => setConfirmDeleteOpen(false)}
          >
            Dismiss
          </Button>
          <Button
            primary
            onClick={handleDelete}
            data-testid={`confirm-delete-${user.username}`}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ManageUserButtons;

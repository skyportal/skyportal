import { useState } from "react";

import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import { useAppDispatch } from "../../types/hooks";
import { groupApi } from "../../ducks/group";
import {
  useDeleteGroupUserMutation,
  useUpdateGroupUserMutation,
} from "../../ducks/groups";

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

  const canSave = (usr: any) => {
    const matchingGroupUser = group?.users?.filter(
      (groupUser) => groupUser["id"] === usr.id,
    )[0];
    return Boolean(matchingGroupUser?.["can_save"]);
  };

  const toggleUserAdmin = async (usr: any) => {
    try {
      await updateGroupUser({
        groupID: loadedId,
        params: {
          userID: usr.id,
          admin: !isAdmin(usr),
        },
      }).unwrap();
      dispatch(
        showNotification(
          "User admin status for this group successfully updated.",
        ),
      );
      dispatch(groupApi.util.invalidateTags([{ type: "Group", id: loadedId }]));
    } catch {
      // error notification handled by the API layer
    }
  };

  const toggleUserCanSave = async (usr: any) => {
    try {
      await updateGroupUser({
        groupID: loadedId,
        params: {
          userID: usr.id,
          canSave: !canSave(usr),
        },
      }).unwrap();
      dispatch(
        showNotification(
          "User's save access status for this group successfully updated.",
        ),
      );
      dispatch(groupApi.util.invalidateTags([{ type: "Group", id: loadedId }]));
    } catch {
      // error notification handled by the API layer
    }
  };

  const handleDelete = () => {
    deleteGroupUser({
      userID: user.id,
      group_id: group.id,
    });
  };

  return (
    <div>
      {isAdmin(currentUser) && (
        <>
          <Button
            size="small"
            onClick={() => {
              toggleUserAdmin(user);
            }}
            disabled={isAdmin(user) && numAdmins === 1}
            sx={{ color: isAdmin(user) ? "#d32f2f" : "#2e7d32" }}
          >
            {`${isAdmin(user) ? "Revoke" : "Grant"} admin status`}
          </Button>
          &nbsp;|&nbsp;
          <Tooltip title="Manage whether user can save sources to this group.">
            <Button
              size="small"
              onClick={() => toggleUserCanSave(user)}
              sx={{ color: canSave(user) ? "#d32f2f" : "#2e7d32" }}
            >
              {`${canSave(user) ? "Revoke" : "Grant"} save access`}
            </Button>
          </Tooltip>
          &nbsp;|&nbsp;
        </>
      )}
      <IconButton
        edge="end"
        aria-label="delete"
        data-testid={`delete-${user.username}`}
        onClick={() => setConfirmDeleteOpen(true)}
        disabled={isAdmin(user) && numAdmins === 1}
        size="large"
      >
        <DeleteIcon />
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
    </div>
  );
};

export default ManageUserButtons;

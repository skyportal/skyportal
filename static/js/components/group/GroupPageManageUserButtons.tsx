import { useState } from "react";

import { useNavigate } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import Typography from "@mui/material/Typography";

import Button from "../Button";

import { useDeleteGroupUserMutation } from "../../ducks/groups";

interface ManageUserButtonsProps {
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
  user,
  isAdmin,
  currentUser,
}: ManageUserButtonsProps) => {
  const navigate = useNavigate();
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

  const handleDelete = () => {
    if (user.username === currentUser.username) navigate("/groups");
    deleteGroupUser({
      userID: user.id,
      group_id: group.id,
    });
  };

  return (
    <>
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
    </>
  );
};

export default ManageUserButtons;

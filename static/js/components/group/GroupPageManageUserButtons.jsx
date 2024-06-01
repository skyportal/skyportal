import React, { useState } from "react";
import PropTypes from "prop-types";

import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import * as groupActions from "../../ducks/group";
import * as groupsActions from "../../ducks/groups";

const ManageUserButtons = ({ group, loadedId, user, isAdmin, currentUser }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const handleConfirmDeleteDialogClose = () => {
    setConfirmDeleteOpen(false);
  };

  let numAdmins = 0;
  group?.users?.forEach((groupUser) => {
    if (groupUser?.admin) {
      numAdmins += 1;
    }
  });

  const canSave = (usr) => {
    const matchingGroupUser = group?.users?.filter(
      (groupUser) => groupUser.id === usr.id,
    )[0];
    return Boolean(matchingGroupUser?.can_save);
  };

  const toggleUserAdmin = async (usr) => {
    const result = await dispatch(
      groupsActions.updateGroupUser(loadedId, {
        userID: usr.id,
        admin: !isAdmin(usr),
      }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification(
          "User admin status for this group successfully updated.",
        ),
      );
      dispatch(groupActions.fetchGroup(loadedId));
    }
  };

  const toggleUserCanSave = async (usr) => {
    const result = await dispatch(
      groupsActions.updateGroupUser(loadedId, {
        userID: usr.id,
        canSave: !canSave(usr),
      }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification(
          "User's save access status for this group successfully updated.",
        ),
      );
      dispatch(groupActions.fetchGroup(loadedId));
    }
  };

  const handleDelete = () => {
    navigate("/groups");
    dispatch(
      groupsActions.deleteGroupUser({
        userID: user.id,
        group_id: group.id,
      }),
    );
  };

  return (
    <div>
      {isAdmin(currentUser) && (
        <div>
          <Button
            size="small"
            onClick={() => {
              toggleUserAdmin(user);
            }}
            disabled={isAdmin(user) && numAdmins === 1}
          >
            <span style={{ whiteSpace: "nowrap" }}>
              {isAdmin(user) ? "Revoke admin status" : "Grant admin status"}
            </span>
          </Button>
          &nbsp;|&nbsp;
          <Tooltip title="Manage whether user can save sources to this group.">
            <Button
              size="small"
              onClick={() => {
                toggleUserCanSave(user);
              }}
            >
              <span style={{ whiteSpace: "nowrap" }}>
                {canSave(user) ? "Revoke save access" : "Grant save access"}
              </span>
            </Button>
          </Tooltip>
          &nbsp;|&nbsp;
        </div>
      )}
      {(isAdmin(currentUser) || user.username === currentUser.username) && (
        <div>
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
                    Warning! This will delete you from the group and all of its
                    filters.
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
                    Warning! This will delete the user from this group and all
                    of its filters.
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
      )}
    </div>
  );
};

ManageUserButtons.propTypes = {
  loadedId: PropTypes.number.isRequired,
  user: PropTypes.shape({
    id: PropTypes.number,
    username: PropTypes.string,
  }).isRequired,
  isAdmin: PropTypes.func.isRequired,
  group: PropTypes.shape({
    id: PropTypes.number,
    users: PropTypes.arrayOf(
      PropTypes.shape({ admin: PropTypes.bool.isRequired }),
    ),
  }).isRequired,
  currentUser: PropTypes.shape({
    id: PropTypes.number,
    username: PropTypes.string,
  }).isRequired,
};

export default ManageUserButtons;

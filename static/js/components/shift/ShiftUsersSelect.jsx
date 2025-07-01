import { useDispatch } from "react-redux";
import React, { useState } from "react";
import {
  addShiftUser,
  deleteShiftUser,
  updateShiftUser,
} from "../../ducks/shifts";
import PropTypes from "prop-types";
import Tooltip from "@mui/material/Tooltip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Checkbox from "@mui/material/Checkbox";
import ListItemIcon from "@mui/material/ListItemIcon";
import Remove from "@mui/icons-material/Remove";
import Add from "@mui/icons-material/Add";
import ListItemText from "@mui/material/ListItemText";
import { showNotification } from "../../../../baselayer/static/js/components/Notifications";
import { userLabel } from "../../utils/format";
import Button from "../Button";

// Returns users in the shift group and that are either in the shift or have not expired
const getShiftGroupUsersFiltered = (shift) => {
  return (shift.group?.group_users || []).filter((user) => {
    const isInShift = shift.shift_users?.some((su) => su.user_id === user.id);
    const isExpired =
      user.expiration_date &&
      new Date(user.expiration_date).getTime() < Date.now();
    return isInShift || !isExpired;
  });
};

// This component allows to add or remove users from one shift or multiple recurring shifts.
function ShiftUsersSelect({ shiftsToManage, usersType = "members" }) {
  const dispatch = useDispatch();
  const [selected, setSelected] = useState([]);
  if (!shiftsToManage || shiftsToManage.length === 0) return;
  // We use only the first shift to populate the users list
  const users = getShiftGroupUsersFiltered(shiftsToManage[0]);
  function userInShift(user, asAdmin = false) {
    return shiftsToManage[0].shift_users.find(
      (shiftUser) =>
        shiftUser.user_id === user.id && (!asAdmin || shiftUser.admin),
    );
  }

  const addUsersToShift = (selected_users, asAdmin = false) => {
    shiftsToManage.forEach((shift) => {
      let users_to_add = [];
      const users_to_update = [];
      selected_users.forEach((user) => {
        (userInShift(user) ? users_to_update : users_to_add).push(user);
      });

      if (!asAdmin) {
        const remainingSlots =
          shift.required_users_number - (shift.shift_users_ids?.length || 0);
        if (users_to_add.length > remainingSlots) {
          users_to_add = users_to_add.slice(0, remainingSlots);
          dispatch(
            showNotification(
              `You selected more users than available slots on ${shift.name}. Only remaining users will be added.`,
              "warning",
            ),
          );
        }
      }

      [...users_to_add, ...users_to_update].forEach((user) => {
        // If the user is already in the shift, we don't add them, but we update their admin status
        const functionToDispatch =
          userInShift(user) && asAdmin ? updateShiftUser : addShiftUser;
        dispatch(
          functionToDispatch({
            shiftID: shift.id,
            userID: user.id,
            admin: asAdmin,
          }),
        ).then((response) => {
          if (response.status === "success") {
            dispatch(
              showNotification(
                `User added to shift '${shift.name}' as ${
                  asAdmin ? "admin" : "member"
                }`,
              ),
            );
          } else {
            dispatch(
              showNotification(
                `Error adding user to shift '${shift.name}' as ${
                  asAdmin ? "admin" : "member"
                }`,
                "error",
              ),
            );
          }
        });
      });
    });
  };

  function removeUsersFromShift(selected_users, asAdmin = false) {
    Object.keys(selected_users).forEach((user) => {
      shiftsToManage.forEach((shift) => {
        const functionToDispatch = asAdmin
          ? updateShiftUser({
              shiftID: shift.id,
              userID: selected_users[user].id,
              admin: false,
            })
          : deleteShiftUser({
              userID: selected_users[user].id,
              shiftID: shift.id,
            });
        dispatch(functionToDispatch).then((result) => {
          if (result.status === "success") {
            dispatch(
              showNotification(
                `User ${selected_users[user]?.username} removed from shift '${
                  shift.name
                }'${asAdmin ? " as admin" : ""}`,
              ),
            );
          } else {
            dispatch(
              showNotification(
                `Error removing user ${
                  selected_users[user]?.username
                } from shift '${shift.name}'${asAdmin ? " as admin" : ""}`,
                "error",
              ),
            );
          }
        });
      });
    });
  }

  function addUserButton(selected_users, asAdmin = false) {
    const usersToAdd =
      selected_users.length > 0
        ? selected_users.filter((user) => !userInShift(user, asAdmin))
        : [];
    let tooltipText;

    if (selected_users.length > 0) {
      tooltipText =
        usersToAdd.length > 0
          ? "Adds selected users to shift"
          : "All the users you selected are already in the shift";
    } else {
      tooltipText = `No users selected, select users to add them to the shift`;
    }
    return (
      <Tooltip title={tooltipText}>
        <span>
          <Button
            sx={{ height: "100%" }}
            color="success"
            variant="outlined"
            id={`add-${asAdmin ? "admins" : "members"}-button`}
            disabled={usersToAdd.length === 0}
            onClick={() => {
              if (usersToAdd.length > 0) {
                addUsersToShift(usersToAdd, asAdmin);
                setSelected((prev) =>
                  prev.filter(
                    (user) => !usersToAdd.some((u) => u.id === user.id),
                  ),
                );
              }
            }}
          >
            Add
          </Button>
        </span>
      </Tooltip>
    );
  }

  function removeUserButton(selected_users, asAdmin = false) {
    const usersToRemove =
      selected_users.length > 0
        ? selected_users.filter((user) => userInShift(user, asAdmin))
        : [];
    let tooltipText;

    if (selected_users.length > 0) {
      tooltipText =
        usersToRemove.length > 0
          ? "Removes selected users from shift"
          : "None of the users you selected are in the shift";
    } else {
      tooltipText = `No users selected, select users to remove them from the shift`;
    }

    return (
      <Tooltip title={tooltipText}>
        <span>
          <Button
            sx={{ height: "100%" }}
            color="error"
            variant="outlined"
            id={`remove-${asAdmin ? "admins" : "members"}-button`}
            disabled={usersToRemove.length === 0}
            onClick={() => {
              if (usersToRemove.length > 0) {
                removeUsersFromShift(usersToRemove);
                setSelected((prev) =>
                  prev.filter(
                    (user) => !usersToRemove.some((u) => u.id === user.id),
                  ),
                );
              }
            }}
          >
            Remove
          </Button>
        </span>
      </Tooltip>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        width: "100%",
        gap: "0.5rem",
      }}
    >
      <FormControl sx={{ width: "60%" }}>
        <InputLabel id={`select-${usersType}-label`}>
          Select {usersType} to manage
        </InputLabel>
        <Select
          labelId={`select-${usersType}-label`}
          label={`Select ${usersType} to manage`}
          multiple
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          renderValue={(usersToManage) => (
            <Box>
              {usersToManage.map((user) => (
                <Chip
                  key={user.id}
                  id={user.id}
                  label={userLabel(user, true, true)}
                  sx={{
                    backgroundColor: userInShift(user, usersType === "admins")
                      ? "#f6b4b4"
                      : "#a5d6a7",
                  }}
                />
              ))}
            </Box>
          )}
          MenuProps={{ PaperProps: { style: { maxHeight: "25vh" } } }}
        >
          {users.map((user) => (
            <MenuItem id={`select-${usersType}`} key={user.id} value={user}>
              <Checkbox checked={selected.some((s) => s.id === user.id)} />
              <ListItemIcon>
                {userInShift(user, usersType === "admins") ? (
                  <Remove style={{ color: "red" }} />
                ) : (
                  <Add style={{ color: "green" }} />
                )}
              </ListItemIcon>
              <ListItemText
                id={user.id}
                primary={userLabel(user, true, true)}
              />
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {addUserButton(selected, usersType === "admins")}
      {removeUserButton(selected, usersType === "admins")}
    </div>
  );
}

ShiftUsersSelect.propTypes = {
  shiftsToManage: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      group: PropTypes.shape({
        group_users: PropTypes.arrayOf(
          PropTypes.shape({
            id: PropTypes.string.isRequired,
            username: PropTypes.string.isRequired,
            expiration_date: PropTypes.string,
          }),
        ),
      }),
      group_id: PropTypes.string,
      required_users_number: PropTypes.number.isRequired,
      shift_users: PropTypes.arrayOf(
        PropTypes.shape({
          user_id: PropTypes.string.isRequired,
          admin: PropTypes.bool.isRequired,
        }),
      ).isRequired,
    }),
  ),
  usersType: PropTypes.string,
};

export default ShiftUsersSelect;

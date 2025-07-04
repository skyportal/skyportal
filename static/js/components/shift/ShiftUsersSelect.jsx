import { useDispatch, useSelector } from "react-redux";
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
  const currentUser = useSelector((state) => state.profile);
  const [selectedIds, setSelectedIds] = useState([]);

  if (!shiftsToManage || shiftsToManage.length === 0) return;
  // We use only the first shift to populate the users list
  const users = getShiftGroupUsersFiltered(shiftsToManage[0]);
  // If the current user is not in the list, we add him to the users list
  if (!users.some((user) => user.id === currentUser.id))
    users.push(currentUser);

  function userInShift(userId, asAdmin = false) {
    return shiftsToManage[0].shift_users.some(
      (shiftUser) =>
        shiftUser.user_id === userId && (!asAdmin || shiftUser.admin),
    );
  }

  const addUsersToShift = (userIdsToAdd, asAdmin = false) => {
    shiftsToManage.forEach((shift) => {
      // If the user is already in the shift, we don't add them, but we update their admin status
      let userIdsToUpdate = userIdsToAdd.filter((uId) => userInShift(uId));
      let userIdsToCreate = userIdsToAdd.filter((uId) => !userInShift(uId));

      if (!asAdmin && shift.required_users_number) {
        const remainingSlots =
          shift.required_users_number - (shift.shift_users_ids?.length || 0);
        if (userIdsToCreate.length > remainingSlots) {
          userIdsToCreate = userIdsToCreate.slice(0, remainingSlots);
          dispatch(
            showNotification(
              `You selected more users than available slots on ${shift.name}. Only remaining users will be added.`,
              "warning",
            ),
          );
        }
      }

      [...userIdsToUpdate, ...userIdsToCreate].forEach((userId) => {
        const functionToDispatch = userIdsToUpdate.includes(userId)
          ? updateShiftUser
          : addShiftUser;
        dispatch(
          functionToDispatch({
            shiftID: shift.id,
            userID: userId,
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

  function removeUsersFromShift(usersIdToRemove, asAdmin = false) {
    usersIdToRemove.forEach((userId) => {
      shiftsToManage.forEach((shift) =>
        dispatch(deleteShiftUser({ userID: userId, shiftID: shift.id })).then(
          (result) => {
            if (result.status === "success") {
              dispatch(
                showNotification(
                  `User removed from shift '${shift.name}'${
                    asAdmin ? " as admin" : ""
                  }`,
                ),
              );
            } else {
              dispatch(
                showNotification(
                  `Error removing user from shift '${shift.name}'${
                    asAdmin ? " as admin" : ""
                  }`,
                  "error",
                ),
              );
            }
          },
        ),
      );
    });
  }

  function manageUsersButton(userIdsToManage, asAdmin = false, isAdd = true) {
    // For 'add', keep users not in the shift; for 'remove', keep users in the shift
    userIdsToManage = userIdsToManage.filter(
      (userId) => userInShift(userId, asAdmin) !== isAdd,
    );
    return (
      <Tooltip
        title={
          userIdsToManage.length === 0
            ? `No users selected, select users
            ${
              isAdd
                ? "not in the shift to add them"
                : "in the shift to remove them"
            }`
            : ""
        }
      >
        <span>
          <Button
            sx={{ height: "100%" }}
            color={isAdd ? "success" : "error"}
            variant="outlined"
            id={`${isAdd ? "add" : "remove"}-${
              asAdmin ? "admins" : "members"
            }-button`}
            disabled={userIdsToManage.length === 0}
            onClick={() => {
              if (userIdsToManage.length > 0) {
                if (isAdd) addUsersToShift(userIdsToManage, asAdmin);
                else removeUsersFromShift(userIdsToManage, asAdmin);
                setSelectedIds(
                  selectedIds.filter((id) => !userIdsToManage.includes(id)),
                );
              }
            }}
          >
            {isAdd ? "Add" : "Remove"}
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
          value={selectedIds}
          onChange={(e) => setSelectedIds(e.target.value)}
          renderValue={(userIdsToManage) => (
            <Box>
              {userIdsToManage.map((userId) => (
                <Chip
                  key={userId}
                  id={userId}
                  label={userLabel(
                    users.find((u) => u.id === userId),
                    true,
                    true,
                  )}
                  sx={{
                    backgroundColor: userInShift(userId, usersType === "admins")
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
            <MenuItem id={`select-${usersType}`} key={user.id} value={user.id}>
              <Checkbox checked={selectedIds.includes(user.id)} />
              <ListItemIcon>
                {userInShift(user.id, usersType === "admins") ? (
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
      {manageUsersButton(selectedIds, usersType === "admins", true)}
      {manageUsersButton(selectedIds, usersType === "admins", false)}
    </div>
  );
}

ShiftUsersSelect.propTypes = {
  shiftsToManage: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      group: PropTypes.shape({
        group_users: PropTypes.arrayOf(
          PropTypes.shape({
            id: PropTypes.number.isRequired,
            username: PropTypes.string.isRequired,
            expiration_date: PropTypes.string,
          }),
        ),
      }),
      group_id: PropTypes.number,
      required_users_number: PropTypes.number,
      shift_users: PropTypes.arrayOf(
        PropTypes.shape({
          user_id: PropTypes.number.isRequired,
          admin: PropTypes.bool.isRequired,
        }),
      ).isRequired,
    }),
  ),
  usersType: PropTypes.string,
};

export default ShiftUsersSelect;

import { useGetProfileQuery, useIsReadOnly } from "../../ducks/profile";
import { useAppDispatch } from "../../types/hooks";
import { useState } from "react";
import {
  useAddShiftUserMutation,
  useDeleteShiftUserMutation,
  useUpdateShiftUserMutation,
} from "../../ducks/shifts";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import Checkbox from "@mui/material/Checkbox";
import ListItemIcon from "@mui/material/ListItemIcon";
import Remove from "@mui/icons-material/Remove";
import Add from "@mui/icons-material/Add";
import ListItemText from "@mui/material/ListItemText";
import { showNotification } from "baselayer/components/Notifications";
import { userLabel } from "../../utils/format";
import Button from "../Button";
import SearchableValueSelect from "../SearchableValueSelect";

// Returns users in the shift group and that are either in the shift or have not expired
const getShiftGroupUsersFiltered = (shift: any) => {
  return (shift.group?.group_users || []).filter((user: any) => {
    const isInShift = shift.shift_users?.some(
      (su: any) => su.user_id === user.id,
    );
    const isExpired =
      user.expiration_date &&
      new Date(user.expiration_date).getTime() < Date.now();
    return isInShift || !isExpired;
  });
};

interface ShiftUsersSelectProps {
  shiftsToManage?: any[] | undefined;
  usersType?: string | undefined;
}

// This component allows to add or remove users from one shift or multiple recurring shifts.
function ShiftUsersSelect({
  shiftsToManage,
  usersType = "members",
}: ShiftUsersSelectProps) {
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const isReadOnly = useIsReadOnly();
  const [addShiftUser] = useAddShiftUserMutation();
  const [deleteShiftUser] = useDeleteShiftUserMutation();
  const [updateShiftUser] = useUpdateShiftUserMutation();
  const [selectedIds, setSelectedIds] = useState<any[]>([]);

  if (isReadOnly) return null;
  if (!shiftsToManage || shiftsToManage.length === 0) return;
  // We use only the first shift to populate the users list
  const users = getShiftGroupUsersFiltered(shiftsToManage[0]);
  // If the current user is not in the list, we add him to the users list
  if (!users.some((user: any) => user.id === currentUser?.id))
    users.push(currentUser);

  function userInShift(userId: any, asAdmin = false) {
    return shiftsToManage![0].shift_users.some(
      (shiftUser: any) =>
        shiftUser.user_id === userId && (!asAdmin || shiftUser.admin),
    );
  }

  const addUsersToShift = (userIdsToAdd: any[], asAdmin = false) => {
    shiftsToManage!.forEach((shift: any) => {
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

      [...userIdsToUpdate, ...userIdsToCreate].forEach(async (userId) => {
        const mutationTrigger = userIdsToUpdate.includes(userId)
          ? updateShiftUser
          : addShiftUser;
        try {
          await mutationTrigger({
            shiftID: shift.id,
            userID: userId,
            admin: asAdmin,
          }).unwrap();
          dispatch(
            showNotification(
              `User added to shift '${shift.name}' as ${
                asAdmin ? "admin" : "member"
              }`,
            ),
          );
        } catch {
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
  };

  function removeUsersFromShift(usersIdToRemove: any[], asAdmin = false) {
    usersIdToRemove.forEach((userId) => {
      shiftsToManage!.forEach(async (shift: any) => {
        try {
          await deleteShiftUser({
            userID: userId,
            shiftID: shift.id,
          }).unwrap();
          dispatch(
            showNotification(
              `User removed from shift '${shift.name}'${
                asAdmin ? " as admin" : ""
              }`,
            ),
          );
        } catch {
          dispatch(
            showNotification(
              `Error removing user from shift '${shift.name}'${
                asAdmin ? " as admin" : ""
              }`,
              "error",
            ),
          );
        }
      });
    });
  }

  function manageUsersButton(
    userIdsToManage: any[],
    asAdmin = false,
    isAdd = true,
  ) {
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
      <SearchableValueSelect
        id={`select-${usersType}`}
        label={`Select ${usersType} to manage`}
        multiple
        options={users}
        value={selectedIds}
        onChange={setSelectedIds}
        getOptionLabel={(user: any) => userLabel(user, true, true)}
        renderValue={(selected: any[], getItemProps: any) =>
          selected.map((user: any, index: number) => {
            const { key, ...itemProps } = getItemProps({ index });
            return (
              <Chip
                key={key}
                {...itemProps}
                size="small"
                label={userLabel(user, true, true)}
                sx={{
                  backgroundColor: userInShift(user.id, usersType === "admins")
                    ? "#f6b4b4"
                    : "#a5d6a7",
                }}
              />
            );
          })
        }
        renderOptionContent={(user: any) => (
          <>
            <Checkbox checked={selectedIds.includes(user.id)} />
            <ListItemIcon>
              {userInShift(user.id, usersType === "admins") ? (
                <Remove style={{ color: "red" }} />
              ) : (
                <Add style={{ color: "green" }} />
              )}
            </ListItemIcon>
            <ListItemText id={user.id} primary={userLabel(user, true, true)} />
          </>
        )}
        sx={{ width: "60%" }}
      />
      {manageUsersButton(selectedIds, usersType === "admins", true)}
      {manageUsersButton(selectedIds, usersType === "admins", false)}
    </div>
  );
}

export default ShiftUsersSelect;

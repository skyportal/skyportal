import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import Chip from "@mui/material/Chip";
import Checkbox from "@mui/material/Checkbox";
import Box from "@mui/material/Box";
import ListItemText from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import UpdateShift from "./UpdateShift";
import ShiftUsersSelect from "./ShiftUsersSelect";
import Button from "../Button";
import {
  addShiftUser,
  deleteShiftUser,
  updateShiftUser,
} from "../../ducks/shifts";
import { deleteShift } from "../../ducks/shifts";
import { userLabel } from "../../utils/format";
import Typography from "@mui/material/Typography";
import { useAppDispatch, useAppSelector } from "../../types/hooks";

const formatUTC = (date: Date) =>
  date.toLocaleString("en-US", {
    timeZone: "UTC",
    dateStyle: "short",
    timeStyle: "short",
    hour12: false,
  });

function repeatedShiftInfos(shift: any) {
  // Add Z to the date to ensure it is treated as UTC
  const start = new Date(`${shift.start_date}Z`);
  const end = new Date(`${shift.end_date}Z`);

  const match = shift.name?.match(/(\d+)\/(\d+)/);
  if (!match) return null;

  const oneHour = 60 * 60 * 1000; // milliseconds in an hour
  const durationInHours = (end.getTime() - start.getTime()) / oneHour;

  const shiftIndex = parseInt(match[1], 10);
  const totalRepetitions = parseInt(match[2], 10);
  // Move start date back to the first shift based on this shift's index in the series
  start.setTime(start.getTime() - (shiftIndex - 1) * durationInHours * oneHour);
  // Move end date forward to the last shift based on the total number of repetitions
  end.setTime(start.getTime() + totalRepetitions * durationInHours * oneHour);
  const repeatedShiftRange = `shifts from ${formatUTC(start)} to ${formatUTC(
    end,
  )}`;

  if (durationInHours === 168) return `Weekly ${repeatedShiftRange}`;
  if (durationInHours === 24) return `Daily ${repeatedShiftRange}`;
  return `${durationInHours.toFixed(1)} hours ${repeatedShiftRange}`;
}

interface ShiftManagementProps {
  shiftToManage: any;
}

const ShiftManagement = ({ shiftToManage }: ShiftManagementProps) => {
  const currentUser = useAppSelector((state) => state.profile);
  const dispatch = useAppDispatch();

  const deleteAShift = (shift: any) => {
    dispatch(deleteShift(shift.id)).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification("Shift deleted"));
      }
    });
  };

  const joinShift = (shift: any) => {
    dispatch(
      addShiftUser({
        userID: currentUser.id,
        admin: false,
        shiftID: shift.id,
      }),
    ).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification(`joined shift: ${shift.name}`));
      }
    });
  };

  function ReplaceUserMenu() {
    const [selectedId, setSelectedId] = useState<any>(null);
    const usersToReplace = shiftToManage.shift_users.filter(
      (shiftUser: any) => shiftUser.needs_replacement,
    );

    function replaceUserInShift(selectedUserId: any) {
      const shiftID = parseInt(shiftToManage.id, 10);
      const shiftUser = usersToReplace.find(
        (u: any) => u.id === selectedUserId,
      );
      dispatch(
        deleteShiftUser({
          userID: shiftUser.user_id,
          shiftID,
        }),
      ).then((result: any) => {
        if (result.status === "success") {
          dispatch(
            addShiftUser({
              shiftID,
              userID: currentUser.id,
              admin: false,
              needs_replacement: false,
            }),
          ).then((next_result: any) => {
            if (next_result.status === "success") {
              dispatch(
                showNotification(`replaced user: ${shiftUser.username}`),
              );
            }
          });
        }
      });
    }

    const currentUserIsMemberInShift = shiftToManage.shift_users.some(
      (shiftUser: any) =>
        shiftUser.user_id === currentUser.id && !shiftUser.admin,
    );
    if (currentUserIsMemberInShift) {
      // check if the user has already asked for a replacement
      if (
        usersToReplace.some(
          (shiftUser: any) => shiftUser.user_id === currentUser.id,
        )
      )
        return null;

      return (
        <Tooltip title="Ask for someone to replace you. All users from the group associated to the Shift will be notified">
          <Button
            primary
            variant="outlined"
            id="ask-for-replacement-button"
            onClick={() => {
              const shiftID = parseInt(shiftToManage.id, 10);
              const userID = parseInt(currentUser.id as any, 10);
              dispatch(
                updateShiftUser({
                  shiftID,
                  userID,
                  admin: false,
                  needs_replacement: true,
                }),
              ).then((result: any) => {
                if (result.status === "success") {
                  dispatch(showNotification(`asked for replacement`));
                }
              });
            }}
          >
            Ask for Replacement
          </Button>
        </Tooltip>
      );
    } else if (usersToReplace.length === 0) return;

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
          <InputLabel id="select-user-replace-label">Replace user</InputLabel>
          <Select
            labelId="select-user-replace-label"
            label="Replace user"
            value={selectedId || ""}
            onChange={(e) => setSelectedId(e.target.value)}
            renderValue={(selectedIdValue: any) => {
              const shiftUser = usersToReplace.find(
                (u: any) => u.id === selectedIdValue,
              );
              return (
                <Box>
                  {selectedIdValue && (
                    <Chip
                      id={selectedIdValue.id}
                      label={userLabel(shiftUser, true)}
                    />
                  )}
                </Box>
              );
            }}
            MenuProps={{ PaperProps: { style: { maxHeight: "25vh" } } }}
          >
            {usersToReplace.map((shiftUser: any) => (
              <MenuItem key={shiftUser.id} value={shiftUser.id}>
                <Checkbox checked={selectedId === shiftUser.id} />
                <ListItemText
                  id={shiftUser.id}
                  primary={userLabel(shiftUser, true)}
                />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Tooltip
          style={{ flex: 1 }}
          title={
            !selectedId ? "No users selected, select users to replace them" : ""
          }
        >
          <div>
            <Button
              sx={{ width: "100%", height: "100%" }}
              primary
              variant="outlined"
              disabled={!selectedId}
              onClick={() => {
                replaceUserInShift(selectedId);
                setSelectedId(null);
              }}
            >
              Replace
            </Button>
          </div>
        </Tooltip>
      </div>
    );
  }

  const leaveShift = (shift: any) => {
    dispatch(
      deleteShiftUser({ userID: currentUser.id, shiftID: shift.id }),
    ).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification(`left shift: ${shift.name}`));
      }
    });
  };

  const admins = shiftToManage.shift_users.filter((su: any) => su.admin);
  const members = shiftToManage.shift_users.filter((su: any) => !su.admin);
  const participating = shiftToManage.shift_users.some(
    (su: any) => su.user_id === currentUser.id,
  );

  let currentUserIsAdminOfShift = false;
  if (
    shiftToManage.shift_users.some(
      (u: any) => u.user_id === currentUser.id && u.admin,
    )
  ) {
    currentUserIsAdminOfShift = true;
  }

  const repeatedShiftDuration = repeatedShiftInfos(shiftToManage);
  const isAdmin =
    currentUserIsAdminOfShift ||
    shiftToManage.group?.has_admin_access ||
    currentUser?.permissions.includes("System admin");
  return (
    <div
      style={
        {
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          "& b": {
            fontWeight: 500,
          },
        } as any
      }
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          width: "100%",
          marginBottom: "1rem",
        }}
      >
        <h2 style={{ margin: "0" }}>
          {shiftToManage.name}
          {isAdmin && <UpdateShift shift={shiftToManage} />}
        </h2>
        <div style={{ display: "flex", gap: "0.3rem" }}>
          {!participating ? (
            <Button
              variant="outlined"
              id="join_button"
              onClick={() => joinShift(shiftToManage)}
            >
              Join
            </Button>
          ) : (
            <Button
              variant="outlined"
              id="leave_button"
              onClick={() => leaveShift(shiftToManage)}
            >
              Leave
            </Button>
          )}
          {isAdmin && (
            <Button
              variant="outlined"
              color="error"
              onClick={() => deleteAShift(shiftToManage)}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
      {shiftToManage.description && (
        <div>
          <b>Description: </b>
          {shiftToManage.description}
        </div>
      )}
      <div>
        <b>Group: </b>
        <Chip
          label={shiftToManage.group?.name}
          color="primary"
          variant="outlined"
        />
      </div>
      <div>
        <b>Admins: </b>
        {admins.map((admin: any) => (
          <Chip
            key={admin.id}
            label={userLabel(admin, true, true)}
            data-testid={`shift-admin-chip-${admin.user_id}`}
            style={{ margin: "0.1rem" }}
          />
        ))}
      </div>
      <div>
        <b>Members: </b>
        {members.map((member: any) => (
          <Chip
            key={member.id}
            label={userLabel(member, true, true)}
            data-testid={`shift-member-chip-${member.user_id}`}
            style={{ margin: "0.1rem" }}
          />
        ))}
      </div>
      {shiftToManage.required_users_number && (
        <div>
          <b>Number of members: </b>
          {shiftToManage.shift_users.length}/
          {shiftToManage.required_users_number}
        </div>
      )}
      <div>
        <b>Start:</b> {formatUTC(new Date(`${shiftToManage.start_date}Z`))}
      </div>
      <div>
        <b>End:</b> {formatUTC(new Date(`${shiftToManage.end_date}Z`))}
      </div>
      {repeatedShiftDuration && (
        <div>
          <b>Repeated shift:</b> {repeatedShiftDuration}
        </div>
      )}
      {isAdmin && (
        <>
          <ShiftUsersSelect
            shiftsToManage={[shiftToManage]}
            usersType="admins"
          />
          <ShiftUsersSelect
            shiftsToManage={[shiftToManage]}
            usersType="members"
          />
        </>
      )}
      <ReplaceUserMenu />
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{
          fontSize: "0.75rem",
          mt: 0.5,
          fontStyle: "italic",
          textAlign: "right",
        }}
      >
        Dates are shown in UTC
      </Typography>
    </div>
  );
};

export default ShiftManagement;

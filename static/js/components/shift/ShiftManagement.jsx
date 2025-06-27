import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import OutlinedInput from "@mui/material/OutlinedInput";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import Chip from "@mui/material/Chip";
import Checkbox from "@mui/material/Checkbox";
import Box from "@mui/material/Box";
import ListItemText from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";
import Add from "@mui/icons-material/Add";
import Remove from "@mui/icons-material/Remove";
import ListItemIcon from "@mui/material/ListItemIcon";
import PropTypes from "prop-types";

import { showNotification } from "baselayer/components/Notifications";
import UpdateShift from "./UpdateShift";
import Button from "../Button";
import {
  addShiftUser,
  deleteShiftUser,
  updateShiftUser,
} from "../../ducks/shifts";
import { deleteShift } from "../../ducks/shift";
import { userLabel } from "../../utils/format";

const useStyles = makeStyles((theme) => ({
  root: {
    marginBottom: theme.spacing(2),
    "& b": {
      fontWeight: 500,
    },
  },
  shiftinfo: {
    margin: "0",
    padding: "0",
  },
  shiftgroup: {
    margin: "0",
    padding: "0",
  },
  content: {
    padding: "1rem",
  },
  buttons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "right",
    gap: "0",
  },
  addUsersElements: {
    display: "flex",
    flexDirection: "column",
  },
  addUsersElement: {
    margin: "0",
    padding: "0.5rem",
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    height: "100%",
  },
  deactivatedButton: {
    margin: "0",
    width: "15%",
    backgroundColor: "#e8eaf6",
  },
  userListItem: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
  },
  addUserListItem: {
    fontSize: "1.25rem",
    marginLeft: "0.5rem",
    color: "green",
    fontWeight: "bold",
  },
  deleteUserListItem: {
    fontSize: "1.25rem",
    marginLeft: "0.5rem",
    color: "red",
    fontWeight: "bold",
  },
  addUserChip: {
    backgroundColor: "#a5d6a7",
  },
  deleteUserChip: {
    backgroundColor: "#ffcdd2",
  },
  replacementButton: {
    alignSelf: "right",
    margin: "0",
    width: "35%",
  },
}));

const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: "25vh",
      overflow: "scroll",
    },
  },
};

function repeatedShiftInfos(shift) {
  const start = new Date(shift.start_date);
  const end = new Date(shift.end_date);

  const match = shift.name?.match(/(\d+)\/(\d+)/);
  if (!match) return null;

  const durationInHours = (end - start) / (60 * 60 * 1000);

  const shiftIndex = parseInt(match[1], 10);
  const totalRepetitions = parseInt(match[2], 10);
  // Move start date back to the first shift based on this shift's index in the series
  start.setHours(start.getHours() - (shiftIndex - 1) * durationInHours);
  // Move end date forward to the last shift based on the total number of repetitions
  end.setHours(
    start.getHours() + (totalRepetitions - shiftIndex) * durationInHours,
  );
  const repeatedShiftRange = `shifts from ${start.toLocaleDateString()} to ${end.toLocaleDateString()} (UTC)`;

  if (durationInHours === 168) return `Weekly ${repeatedShiftRange}`;
  if (durationInHours === 24) return `Daily ${repeatedShiftRange}`;
  return `${durationInHours} hours ${repeatedShiftRange}`;
}

const ShiftManagement = ({ currentShift }) => {
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();

  const currentShiftGroup = currentShift.group;

  let users = currentShiftGroup?.group_users || [];

  // remove users from the users list if they are not already in the shift
  // AND their expiration_date is set AND it is in the past (when compared to the current UTC date)
  users = users.filter(
    (user) =>
      !(
        !currentShift.shift_users.find(
          (shiftUser) => shiftUser.user_id === user.id,
        ) &&
        user.expiration_date &&
        new Date(user.expiration_date).getTime() < new Date().getTime()
      ),
  );

  function MultipleGroupSelectChip() {
    const { selectedUsers } = useSelector((state) => state.shift);
    const [selectedMembers, setSelectedMembers] = useState(selectedUsers || []);
    const [selectedAdmins, setSelectedAdmins] = useState([]);

    const addUsersToShift = (selected_users, asAdmin = false) => {
      if (!selected_users.length) {
        dispatch(showNotification("No users selected", "error"));
        return;
      }

      const remainingSlots =
        currentShift.required_users_number - currentShift.shift_users.length;

      if (remainingSlots <= 0) {
        dispatch(
          showNotification(
            "Shift already full, no users added to shift",
            "warning",
          ),
        );
        return;
      }

      let users_to_add = [];
      const users_to_update = [];
      selected_users.forEach((user) => {
        (userInShift(user) ? users_to_update : users_to_add).push(user);
      });
      if (users_to_add.length > remainingSlots) {
        users_to_add = users_to_add.slice(0, remainingSlots);
        dispatch(
          showNotification(
            "You selected more users than available slots. Adding only remaining users.",
            "warning",
          ),
        );
      }

      [...users_to_add, ...users_to_update].forEach((user) => {
        // If the user is already in the shift, we don't add them, but we update their admin status
        const functionToDispatch =
          userInShift(user) && asAdmin ? updateShiftUser : addShiftUser;
        dispatch(
          functionToDispatch({
            shiftID: currentShift.id,
            userID: user.id,
            admin: asAdmin,
          }),
        ).then((response) => {
          if (response.status === "success") {
            dispatch(
              showNotification(
                `User added to shift as ${asAdmin ? "admin" : "member"}`,
              ),
            );
          } else {
            dispatch(
              showNotification(
                `Error adding user to shift as ${asAdmin ? "admin" : "member"}`,
                "error",
              ),
            );
          }
        });
      });
    };

    function removeUsersFromShift(selected_users, asAdmin = false) {
      if (!selected_users.length) {
        dispatch(showNotification("No users selected", "error"));
        return;
      }

      Object.keys(selected_users).forEach((user) => {
        const functionToDispatch = asAdmin
          ? updateShiftUser({
              shiftID: currentShift.id,
              userID: selected_users[user].id,
              admin: false,
            })
          : deleteShiftUser({
              userID: selected_users[user].id,
              shiftID: currentShift.id,
            });
        dispatch(functionToDispatch).then((result) => {
          if (result.status === "success") {
            dispatch(
              showNotification(
                `User ${selected_users[user]?.username} removed from shift${
                  asAdmin ? " as admin" : ""
                }`,
              ),
            );
          }
        });
      });
    }

    function removeMembersFromSelected(selected_users) {
      if (selected_users.length > 0) {
        const newSelectedUsers = selectedMembers.filter((user) =>
          selected_users.every((selected_user) => selected_user.id !== user.id),
        );
        dispatch({
          type: "skyportal/CURRENT_SHIFT_SELECTED_USERS",
          data: newSelectedUsers,
        });
      }
    }

    function userInShift(user, asAdmin = false) {
      return currentShift.shift_users.find(
        (shiftUser) =>
          shiftUser.user_id === user.id && (!asAdmin || shiftUser.admin),
      );
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
              primary
              id={`${
                usersToAdd.length > 0 ? "" : "deactivated-"
              }add-users-button`}
              disabled={usersToAdd.length === 0}
              onClick={() => {
                if (usersToAdd.length > 0) {
                  addUsersToShift(usersToAdd, asAdmin);
                  if (!asAdmin) {
                    removeMembersFromSelected(usersToAdd);
                  }
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
              secondary
              id={`${
                usersToRemove.length > 0 ? "" : "deactivated-"
              }remove-users-button`}
              disabled={usersToRemove.length === 0}
              onClick={() => {
                if (usersToRemove.length > 0) {
                  removeUsersFromShift(usersToRemove);
                  if (!asAdmin) {
                    removeMembersFromSelected(usersToRemove);
                  }
                }
              }}
            >
              Remove
            </Button>
          </span>
        </Tooltip>
      );
    }

    const manageShiftUsers = ({
      usersType = "users",
      selected,
      setSelected,
    }) => {
      return (
        <div className={classes.addUsersElement}>
          <FormControl sx={{ width: "60%" }}>
            <InputLabel id={`select-${usersType}-label`}>
              Select {usersType}
            </InputLabel>
            <Select
              labelId={`select-${usersType}-label`}
              multiple
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              input={<OutlinedInput label={`Select ${usersType}`} />}
              renderValue={(usersToManage) => (
                <Box>
                  {usersToManage.map((user) => (
                    <Chip
                      key={user.id}
                      id={user.id}
                      label={userLabel(user, true, true)}
                      sx={{
                        backgroundColor: userInShift(
                          user,
                          usersType === "admins",
                        )
                          ? "#f6b4b4"
                          : "#a5d6a7",
                      }}
                    />
                  ))}
                </Box>
              )}
              MenuProps={MenuProps}
            >
              {users.map((user) => (
                <MenuItem id="select_users" key={user.id} value={user}>
                  <Checkbox checked={selected.some((s) => s.id === user.id)} />
                  <ListItemIcon>
                    {userInShift(user, usersType === "admins") ? (
                      <Remove style={{ color: "red" }} />
                    ) : (
                      <Add style={{ color: "green" }} />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    className={classes.userListItem}
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
    };

    return (
      <div className={classes.addUsersElements}>
        {manageShiftUsers({
          usersType: "admins",
          selected: selectedAdmins,
          setSelected: setSelectedAdmins,
        })}
        {manageShiftUsers({
          usersType: "members",
          selected: selectedMembers,
          setSelected: setSelectedMembers,
        })}
      </div>
    );
  }

  const deleteAShift = (shift) => {
    dispatch({ type: "skyportal/FETCH_SHIFT_OK", data: {} });
    dispatch(deleteShift(shift.id)).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Shift deleted"));
      }
    });
  };

  const joinShift = (shift) => {
    dispatch(
      addShiftUser({
        userID: currentUser.id,
        admin: false,
        shiftID: shift.id,
      }),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification(`joined shift: ${shift.name}`));
      }
    });
  };

  function ReplaceUserMenu({ currentUserIsAdminOfShift }) {
    const [selectedToReplace, setSelectedToReplace] = useState({});
    const usersToReplace = currentShift.shift_users.filter(
      (shiftUser) => shiftUser.needs_replacement,
    );
    const currentUserInShift = currentShift.shift_users.some(
      (shiftUser) => shiftUser.user_id === currentUser.id,
    );

    function replaceUserInShift(selected_user) {
      const shiftID = parseInt(currentShift.id, 10);
      dispatch(
        deleteShiftUser({
          userID: selected_user.id,
          shiftID,
        }),
      ).then((result) => {
        if (result.status === "success") {
          dispatch(
            addShiftUser({
              shiftID,
              userID: currentUser.id,
              admin: false,
              needs_replacement: false,
            }),
          ).then((next_result) => {
            if (next_result.status === "success") {
              dispatch(
                showNotification(`replaced user: ${selected_user.username}`),
              );
            }
          });
        }
      });
    }

    const userReplacementButton = () => {
      let button;
      if (Object.keys(selectedToReplace).length > 0) {
        button = (
          <Tooltip title="Replace selected users">
            <Button
              primary
              id="replace-users-button"
              className={classes.activatedButton}
              onClick={() => {
                replaceUserInShift(selectedToReplace);
                setSelectedToReplace({});
              }}
            >
              Replace
            </Button>
          </Tooltip>
        );
      } else {
        button = (
          <Tooltip title="No users selected, select users to replace them">
            <Button
              secondary
              id="deactivated-replace-users-button"
              className={classes.deactivatedButton}
            >
              Replace
            </Button>
          </Tooltip>
        );
      }
      return button;
    };

    const askForReplacementButton = () => {
      let button = null;
      if (currentUserInShift && !currentUserIsAdminOfShift) {
        // check if the user has already asked for a replacement
        const userHasAlreadyAskedForReplacement = usersToReplace.some(
          (shiftUser) => shiftUser.user_id === currentUser.id,
        );
        if (!userHasAlreadyAskedForReplacement) {
          button = (
            <Tooltip title="Ask for someone to replace you. All users from the group associated to the Shift will be notified">
              <Button
                primary
                id="ask-for-replacement-button"
                className={classes.replacementButton}
                onClick={() => {
                  const shiftID = parseInt(currentShift.id, 10);
                  const userID = parseInt(currentUser.id, 10);
                  dispatch(
                    updateShiftUser({
                      shiftID,
                      userID,
                      admin: false,
                      needs_replacement: true,
                    }),
                  ).then((result) => {
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
        }
      }
      return button;
    };

    const handleChangeReplace = (event) => {
      const {
        target: { value },
      } = event;
      if (value) {
        setSelectedToReplace(value);
      } else {
        setSelectedToReplace({});
      }
    };

    return (
      <div>
        {usersToReplace.length > 0 && !currentUserInShift ? (
          <div className={classes.addUsersElements}>
            <FormControl className={classes.addUsersForm}>
              <InputLabel
                className={classes.addUsersLabel}
                id="select-user-replace-label"
              >
                Replace user
              </InputLabel>
              <Select
                labelId="select-user-replace-chip-label"
                id="select-user-replace-chip"
                value={selectedToReplace}
                onChange={handleChangeReplace}
                input={<OutlinedInput id="select-chip" label="Chip" />}
                renderValue={(selectedToReplaceValue) => (
                  <Box id="selected_users">
                    {Object.keys(selectedToReplaceValue).length > 0 && (
                      <Chip
                        key={`${selectedToReplaceValue.id}_selected_to_replace`}
                        id={selectedToReplaceValue.id}
                        label={userLabel(selectedToReplaceValue, true, true)}
                      />
                    )}
                  </Box>
                )}
                MenuProps={MenuProps}
              >
                {usersToReplace.map((user) => (
                  <MenuItem
                    id="select_user_to_replace"
                    key={`${user.id}_can_replace`}
                    value={user}
                  >
                    <Checkbox
                      checked={
                        Object.keys(selectedToReplace).length > 0 &&
                        selectedToReplace.id === user.id
                      }
                    />
                    <ListItemText
                      className={classes.userListItem}
                      id={user.id}
                      primary={userLabel(user, true, true)}
                    />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {userReplacementButton()}
          </div>
        ) : (
          <div className={classes.addUsersElements}>
            {askForReplacementButton()}
          </div>
        )}
      </div>
    );
  }

  ReplaceUserMenu.propTypes = {
    currentUserIsAdminOfShift: PropTypes.bool.isRequired,
  };

  const leaveShift = (shift) => {
    dispatch(
      deleteShiftUser({ userID: currentUser.id, shiftID: shift.id }),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification(`left shift: ${shift.name}`));
      }
    });
  };

  let admins = [];
  let members = [];
  let participating = false;

  if (users.length > 0) {
    admins = currentShift.shift_users
      .filter((shift_user) => shift_user.admin)
      .map((shift_user) => shift_user?.user_id);
    admins = users
      .filter((user) => admins.includes(user.id))
      .map((user) => `${userLabel(user, true, true)}`);

    members = currentShift.shift_users
      .filter((shift_user) => !shift_user.admin)
      .map((shift_user) => shift_user?.user_id);
    members = users
      .filter((user) => members.includes(user.id))
      .map((user) => `${userLabel(user, true, true)}`);

    participating = currentShift.shift_users
      .map((user) => user.user_id)
      .includes(currentUser.id);
  }

  let currentUserIsAdminOfShift = false;
  if (
    currentShift.shift_users.filter(
      (user) => user.user_id === currentUser.id && user.admin,
    ).length > 0
  ) {
    currentUserIsAdminOfShift = true;
  }

  const repeatedShiftDuration = repeatedShiftInfos(currentShift);
  const isAdmin =
    currentUserIsAdminOfShift ||
    currentShiftGroup?.has_admin_access ||
    currentUser?.permissions.includes("System admin");
  return (
    <div className={classes.root}>
      <div
        style={{
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
        }}
      >
        {isAdmin && <UpdateShift shift={currentShift} />}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            width: "100%",
            marginBottom: "1rem",
          }}
        >
          <div>
            <h2 className={classes.shiftinfo}>
              {`${currentShift.name}${
                currentShift.description ? `: ${currentShift.description}` : ""
              }`}
            </h2>
            <h3 className={classes.shiftgroup}>
              Group: {currentShiftGroup?.name}
            </h3>
          </div>
          <div className={classes.buttons}>
            {!participating ? (
              <Button id="join_button" onClick={() => joinShift(currentShift)}>
                Join
              </Button>
            ) : (
              <Button
                variant="outlined"
                primary
                id="leave_button"
                onClick={() => leaveShift(currentShift)}
              >
                Leave
              </Button>
            )}
            {isAdmin && (
              <Button
                variant="outlined"
                color="error"
                style={{ marginLeft: "0.3rem" }}
                onClick={() => deleteAShift(currentShift)}
              >
                Delete
              </Button>
            )}
          </div>
        </div>
        <div>
          <b>Admins: </b>
          {admins.map((admin) => (
            <Chip key={admin} label={admin} />
          ))}
        </div>
        <div>
          <b>Members: </b>
          {members.map((member) => (
            <Chip key={member} label={member} />
          ))}
        </div>
        {currentShift.required_users_number && (
          <div>
            <b>Number of members: </b>
            {currentShift.shift_users.length}/
            {currentShift.required_users_number}
          </div>
        )}
        <div>
          <b>Start:</b> {new Date(currentShift.start_date).toLocaleString()}
        </div>
        <div>
          <b>End:</b> {new Date(currentShift.end_date).toLocaleString()}
        </div>
        {repeatedShiftDuration && (
          <div>
            <b>Repeated shift:</b> {repeatedShiftDuration}
          </div>
        )}
      </div>
      <div className={classes.addUsersElements}>
        {isAdmin && <MultipleGroupSelectChip />}
      </div>
      <ReplaceUserMenu currentUserIsAdminOfShift={currentUserIsAdminOfShift} />
    </div>
  );
};

ShiftManagement.propTypes = {
  currentShift: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    description: PropTypes.string,
    group_id: PropTypes.number,
    group: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
        has_admin_access: PropTypes.bool,
        group_users: PropTypes.arrayOf(
          PropTypes.shape({
            id: PropTypes.number,
            first_name: PropTypes.string,
            last_name: PropTypes.string,
            username: PropTypes.string,
          }),
        ),
      }),
    ),
    start_date: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.instanceOf(Date),
    ]),
    end_date: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.instanceOf(Date),
    ]),
    shift_users: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        admin: PropTypes.bool,
      }),
    ),
    required_users_number: PropTypes.number,
  }).isRequired,
};

export default ShiftManagement;

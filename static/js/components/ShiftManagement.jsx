import React from "react";
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
import PropTypes from "prop-types";

import { showNotification } from "baselayer/components/Notifications";
import UpdateShift from "./UpdateShift";
import Button from "./Button";
import * as shiftActions from "../ducks/shift";
import {
  addShiftUser,
  deleteShiftUser,
  updateShiftUser,
} from "../ducks/shifts";

const useStyles = makeStyles((theme) => ({
  root: {
    marginBottom: theme.spacing(2),
  },
  shiftinfo: {
    margin: "0",
    padding: "0",
  },
  shiftgroup: {
    margin: "0",
    padding: "0",
  },
  shift_content: {
    padding: "1rem",
    paddingBottom: "0",
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
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
    margin: "0",
    padding: "0.5rem",
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    height: "100%",
  },
  activatedButton: {
    margin: "0",
    width: "15%",
  },
  deactivatedButton: {
    margin: "0",
    width: "15%",
    backgroundColor: "#e8eaf6",
  },
  addUsersLabel: {
    margin: "0",
    marginLeft: "1rem",
  },
  addUsersForm: {
    margin: "0",
    width: "60%",
    height: "100%",
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

function isRepeatedShift(shiftName) {
  const regex = /\d+\/\d+/;
  return regex.test(shiftName)
    ? [
        parseInt(shiftName.match(/\d+/)[0], 10),
        parseInt(shiftName.match(/\/\d+/)[0].slice(1), 10),
      ]
    : null;
}

function repeatedShiftStartEnd(shift) {
  const startDate = new Date(shift.start_date);
  const endDate = new Date(shift.end_date);
  const day = isRepeatedShift(shift.name);
  if (day) {
    // if there is more than 24 hours between start and end date, its a weekly shift
    if (endDate.getTime() - startDate.getTime() > 86400000) {
      return [
        `Weekly repeated shift`,
        `Each shift from ${startDate.toLocaleTimeString()} to ${endDate.toLocaleTimeString()} (UTC)`,
      ];
    }
    startDate.setDate(startDate.getDate() - day[0]);
    endDate.setDate(endDate.getDate() - day[0] + day[1]);
    // return a string with start and end date, and a string with start and end time
    return [
      `Daily repeated shifts from ${startDate.toLocaleDateString()} to ${endDate.toLocaleDateString()}`,
      `Each shift from ${startDate.toLocaleTimeString()} to ${endDate.toLocaleTimeString()} (UTC)`,
    ];
  }
  return null;
}

const userLabel = (user) => {
  if (!user) {
    return "";
  }
  let label = user.username;
  if (user.first_name && user.last_name) {
    label = `${user.first_name} ${user.last_name} (${user.username})`;
    if (user.affiliations && user.affiliations.length > 0) {
      label = `${label} (${user.affiliations.join()})`;
    }
  }
  return label;
};

const ShiftManagement = ({ currentShift }) => {
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();

  const currentShiftGroup = currentShift.group;

  const users = currentShiftGroup?.group_users || [];

  function MultipleGroupSelectChip() {
    const { selectedUsers } = useSelector((state) => state.shift);
    const [selected, setSelected] = React.useState(selectedUsers || []);

    const handleChange = (event) => {
      const {
        target: { value },
      } = event;
      const newSelected = [];
      value.forEach((element) => {
        if (!newSelected.find((user) => user.id === element.id)) {
          newSelected.push(element);
        } else {
          newSelected.splice(
            newSelected.findIndex((user) => user.id === element.id),
            1,
          );
        }
      });
      setSelected(newSelected);
    };

    function addUsersToShift(selected_users) {
      if (selected_users.length > 0) {
        const users_to_add = [];
        let counter = currentShift.shift_users.length;
        for (let i = 0; i < selected_users.length; i += 1) {
          if (counter === currentShift.required_users_number) {
            break;
          } else {
            users_to_add.push(selected_users[i]);
            counter += 1;
          }
        }
        if (users_to_add.length > 0) {
          if (users_to_add.length !== selected_users.length) {
            dispatch(
              showNotification(
                "You selected more users than the required number of users for this shift. Adding only the remaining users to the shift.",
                "warning",
              ),
            );
          }
          users_to_add.forEach((user) => {
            dispatch(
              addShiftUser({
                userID: user.id,
                admin: false,
                shiftID: currentShift.id,
              }),
            ).then((response) => {
              if (response.status === "success") {
                dispatch(showNotification("User added to shift"));
              } else {
                dispatch(
                  showNotification("Error adding user to shift", "error"),
                );
              }
            });
          });
        } else {
          dispatch(
            showNotification(
              "Shift already Full, no users added to shift",
              "warning",
            ),
          );
        }
      } else {
        dispatch(showNotification("No users selected", "error"));
      }
    }

    function removeUsersFromShift(selected_users) {
      if (selected_users.length > 0) {
        Object.keys(selected_users).forEach((user) => {
          dispatch(
            deleteShiftUser({
              userID: selected_users[user].id,
              shiftID: currentShift.id,
            }),
          ).then((result) => {
            if (result.status === "success") {
              dispatch(
                showNotification(
                  `User ${selected_users[user]?.username} removed from shift`,
                ),
              );
            }
          });
        });
      } else {
        dispatch(showNotification("No users selected", "error"));
      }
    }

    function removeUsersFromSelected(selected_users) {
      if (selected_users.length > 0) {
        const newSelectedUsers = selected.filter((user) =>
          selected_users.every((selected_user) => selected_user.id !== user.id),
        );
        dispatch({
          type: "skyportal/CURRENT_SHIFT_SELECTED_USERS",
          data: newSelectedUsers,
        });
      }
    }

    function usersNotInShift(user) {
      return (
        !currentShift.shift_users.find(
          (shiftUser) => shiftUser.user_id === user.id,
        ) && currentUser.id !== user.id
      );
    }

    function userManagementAddButton(selected_users) {
      let button;
      if (selected_users.length > 0) {
        const usersToAdd = selected_users.filter(usersNotInShift);
        if (usersToAdd.length > 0) {
          button = (
            <Tooltip title="Adds selected users to shift">
              <Button
                primary
                id="add-users-button"
                className={classes.activatedButton}
                onClick={() => {
                  addUsersToShift(usersToAdd);
                  removeUsersFromSelected(usersToAdd);
                }}
              >
                Add
              </Button>
            </Tooltip>
          );
        } else {
          button = (
            <Tooltip title="All the users you selected are already in the shift">
              <Button
                primary
                id="deactivated-add-users-button"
                className={classes.deactivatedButton}
              >
                Add
              </Button>
            </Tooltip>
          );
        }
      } else {
        button = (
          <Tooltip title="No users selected, select users to add them to the shift">
            <Button
              primary
              id="deactivated-add-users-button"
              className={classes.deactivatedButton}
            >
              Add
            </Button>
          </Tooltip>
        );
      }
      return button;
    }

    function usersInShift(user) {
      return (
        currentShift.shift_users.find(
          (shiftUser) => shiftUser.user_id === user.id,
        ) && currentUser.id !== user.id
      );
    }

    function userManagementRemoveButton(selected_users) {
      let button;
      if (selected_users.length > 0) {
        const usersToRemove = selected_users.filter(usersInShift);
        if (usersToRemove.length > 0) {
          button = (
            <Tooltip title="Removes selected users from shift">
              <Button
                secondary
                id="remove-users-button"
                className={classes.activatedButton}
                onClick={() => {
                  removeUsersFromShift(usersToRemove);
                  removeUsersFromSelected(usersToRemove);
                }}
              >
                Remove
              </Button>
            </Tooltip>
          );
        } else {
          button = (
            <Tooltip title="None of the users you selected are in the shift">
              <Button
                secondary
                id="deactivated-remove-users-button"
                className={classes.deactivatedButton}
              >
                Remove
              </Button>
            </Tooltip>
          );
        }
      } else {
        button = (
          <Tooltip title="No users selected, select users to remove them from the shift">
            <Button
              secondary
              id="deactivated-remove-users-button"
              className={classes.deactivatedButton}
            >
              Remove
            </Button>
          </Tooltip>
        );
      }
      return button;
    }

    function addOrDeleteUserListItem(user) {
      let indicator = <span className={classes.addUserListItem}>+</span>;
      if (usersInShift(user)) {
        indicator = <span className={classes.deleteUserListItem}>-</span>;
      }
      return indicator;
    }

    function addOrDeleteUserChip(user) {
      let style = classes.addUserChip;
      if (usersInShift(user)) {
        style = classes.deleteUserChip;
      }
      return style;
    }

    return (
      <div className={classes.addUsersElements}>
        <FormControl className={classes.addUsersForm}>
          <InputLabel className={classes.addUsersLabel} id="select-users-label">
            Select Users
          </InputLabel>
          <Select
            labelId="select-users-multiple-chip-label"
            id="select-users--multiple-chip"
            multiple
            value={selected}
            onChange={handleChange}
            input={<OutlinedInput id="select-multiple-chip" label="Chip" />}
            renderValue={(selected_users) => (
              <Box id="selected_users">
                {selected_users.map((value) => (
                  <Chip
                    key={value.id}
                    id={value.id}
                    label={userLabel(value)}
                    className={addOrDeleteUserChip(value)}
                  />
                ))}
              </Box>
            )}
            MenuProps={MenuProps}
          >
            {users.map((user) => (
              <MenuItem id="select_users" key={user.id} value={user}>
                <Checkbox
                  checked={selected.some(
                    (selected_user) => selected_user.id === user.id,
                  )}
                />
                <ListItemText
                  className={classes.userListItem}
                  id={user.id}
                  primary={userLabel(user)}
                  secondary={addOrDeleteUserListItem(user)}
                />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {userManagementAddButton(selected)}
        {userManagementRemoveButton(selected)}
      </div>
    );
  }

  const deleteShift = (shift) => {
    dispatch({ type: "skyportal/FETCH_SHIFT_OK", data: {} });
    dispatch(shiftActions.deleteShift(shift.id)).then((result) => {
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
    const [selectedToReplace, setSelectedToReplace] = React.useState({});
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
                      userID,
                      admin: false,
                      needs_replacement: true,
                      shiftID,
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
                        label={userLabel(selectedToReplaceValue)}
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
                      primary={userLabel(user)}
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

  if (currentShift.name != null && users.length > 0) {
    admins = currentShift.shift_users
      .filter((shift_user) => shift_user.admin)
      .map((shift_user) => shift_user?.user_id);
    admins = users
      .filter((user) => admins.includes(user.id))
      .map((user) => `${userLabel(user)}`);

    members = currentShift.shift_users
      .filter((shift_user) => !shift_user.admin)
      .map((shift_user) => shift_user?.user_id);
    members = users
      .filter((user) => members.includes(user.id))
      .map((user) => `${userLabel(user)}`);

    participating = currentShift.shift_users
      .map((user) => user.user_id)
      .includes(currentUser.id);
  }

  let [shiftDateStartEnd, shiftTimeStartEnd] = [null, null];
  if (currentShift.name != null && repeatedShiftStartEnd(currentShift)) {
    [shiftDateStartEnd, shiftTimeStartEnd] =
      repeatedShiftStartEnd(currentShift);
  }

  let currentUserIsAdminOfShift = false;
  if (currentShift.name != null) {
    if (
      currentShift.shift_users.filter(
        (user) => user.user_id === currentUser.id && user.admin,
      ).length > 0
    ) {
      currentUserIsAdminOfShift = true;
    }
  }

  const currentUserIsAdminOfGroup = currentShiftGroup?.has_admin_access;

  return (
    currentShift.name != null && (
      <div id="current_shift" className={classes.root}>
        <div className={classes.shift_content}>
          <div>
            {(currentUserIsAdminOfShift ||
              currentUserIsAdminOfGroup ||
              currentUser?.permissions.includes("System admin")) && (
              <UpdateShift shift={currentShift} />
            )}
            {currentShift.description ? (
              <h2 id="current_shift_title" className={classes.shiftinfo}>
                {currentShift.name}: {currentShift.description}
              </h2>
            ) : (
              <h2
                id="current_shift_title"
                className={classes.shiftinfo}
                key="shift_info"
              >
                {currentShift.name}
              </h2>
            )}
            <h3 id="current_shift_group" className={classes.shiftgroup}>
              {" "}
              Group: {currentShiftGroup?.name}
            </h3>
            <div>
              <i id="current_shift_admins">{`\n Admins : ${admins.join(
                ", ",
              )}`}</i>
            </div>
            <div>
              <i id="current_shift_members">{`\n Members : ${members.join(
                ", ",
              )}`}</i>
            </div>
            {currentShift.required_users_number && (
              <div>
                <i id="total_shift_members">{`\n Number of Members : ${currentShift.shift_users.length}/${currentShift.required_users_number}`}</i>
              </div>
            )}
            {shiftDateStartEnd ? (
              <>
                <p id="current_shift_date" className={classes.shiftgroup}>
                  {shiftDateStartEnd}
                </p>
                <p id="current_shift_time" className={classes.shiftgroup}>
                  {shiftTimeStartEnd}
                </p>
              </>
            ) : (
              <>
                <p id="current_shift_start_date" className={classes.shiftgroup}>
                  Start: {new Date(currentShift.start_date).toLocaleString()}
                </p>
                <p id="current_shift_end_date" className={classes.shiftgroup}>
                  End: {new Date(currentShift.end_date).toLocaleString()}
                </p>
              </>
            )}
          </div>
          <div className={classes.buttons}>
            {!participating && (
              <Button id="join_button" onClick={() => joinShift(currentShift)}>
                Join
              </Button>
            )}
            {participating && (
              <Button
                id="leave_button"
                onClick={() => leaveShift(currentShift)}
              >
                Leave
              </Button>
            )}
            {(currentUserIsAdminOfShift ||
              currentUserIsAdminOfGroup ||
              currentUser?.permissions.includes("System admin")) && (
              <Button
                secondary
                id="delete_button"
                onClick={() => deleteShift(currentShift)}
              >
                Delete
              </Button>
            )}
          </div>
        </div>
        <div className={classes.addUsersElements}>
          {(currentUserIsAdminOfShift ||
            currentUserIsAdminOfGroup ||
            currentUser?.permissions.includes("System admin")) && (
            <MultipleGroupSelectChip id="add_shift_users" />
          )}
        </div>
        <ReplaceUserMenu
          currentUserIsAdminOfShift={currentUserIsAdminOfShift}
        />
      </div>
    )
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

import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import Button from "@material-ui/core/Button";
import OutlinedInput from "@material-ui/core/OutlinedInput";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import FormControl from "@material-ui/core/FormControl";
import Select from "@material-ui/core/Select";
import Chip from "@material-ui/core/Chip";
import Checkbox from "@material-ui/core/Checkbox";
import Box from "@material-ui/core/Box";
import ListItemText from "@material-ui/core/ListItemText";
import Tooltip from "@material-ui/core/Tooltip";
import PropTypes from "prop-types";

import { showNotification } from "baselayer/components/Notifications";
import * as shiftActions from "../ducks/shift";
import {
  addShiftUser,
  deleteShiftUser,
  updateShiftUser,
} from "../ducks/shifts";
import CommentList from "./CommentList";

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

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
    },
  },
};

function isDailyShift(shiftName) {
  const regex = /\d+\/\d+/;
  return regex.test(shiftName)
    ? [
        parseInt(shiftName.match(/\d+/)[0], 10),
        parseInt(shiftName.match(/\/\d+/)[0].slice(1), 10),
      ]
    : null;
}

function dailyShiftStartEnd(shift) {
  const startDate = new Date(shift.start_date);
  const endDate = new Date(shift.end_date);
  const day = isDailyShift(shift.name);
  if (day) {
    startDate.setDate(startDate.getDate() - day[0]);
    endDate.setDate(endDate.getDate() - day[0] + day[1]);
    // return a string with start and end date, and a string with start and end time
    return [
      `Daily shifts from ${startDate.toLocaleDateString()} to ${endDate.toLocaleDateString()}`,
      `Each shift from ${startDate.toLocaleTimeString()} to ${endDate.toLocaleTimeString()}`,
    ];
  }
  return null;
}

const userLabel = (user) => {
  let label = user.username;
  if (user.first_name && user.last_name) {
    label = `${user.first_name} ${user.last_name} (${user.username})`;
  }
  return label;
};

export function CurrentShiftMenu({ currentShift }) {
  const classes = useStyles();
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();

  function MultipleGroupSelectChip() {
    const users = currentShift.group.group_users.filter(
      (user) => user.id !== currentUser.id
    );
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
            1
          );
        }
      });
      setSelected(newSelected);
    };

    function addUsersToShift(selected_users) {
      if (selected_users.length > 0) {
        Object.keys(selected_users).forEach((user) => {
          dispatch(
            addShiftUser({
              userID: selected_users[user].id,
              admin: false,
              shift_id: currentShift.id,
            })
          );
        });
        dispatch(showNotification("Users added to shift"));
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
              shift_id: currentShift.id,
            })
          ).then((result) => {
            if (result.status === "success") {
              dispatch(
                showNotification(
                  `User ${selected_users[user]?.username} removed from shift`
                )
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
          selected_users.every((selected_user) => selected_user.id !== user.id)
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
          (shiftUser) => shiftUser.id === user.id
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
                id="add-users-button"
                variant="contained"
                color="primary"
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
                id="deactivated-add-users-button"
                variant="contained"
                color="secondary"
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
              id="deactivated-add-users-button"
              variant="contained"
              color="secondary"
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
          (shiftUser) => shiftUser.id === user.id
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
                id="remove-users-button"
                variant="contained"
                color="primary"
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
                id="deactivated-remove-users-button"
                variant="contained"
                color="secondary"
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
              id="deactivated-remove-users-button"
              variant="contained"
              color="secondary"
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
                    (selected_user) => selected_user.id === user.id
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
    dispatch({ type: "skyportal/CURRENT_SHIFT", data: {} });
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
        shift_id: shift.id,
      })
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification(`joined shift: ${shift.name}`));
      }
    });
  };

  function ReplaceUserMenu({ currentUserIsAdminOfShift }) {
    const [selectedToReplace, setSelectedToReplace] = React.useState({});
    const usersToReplace = currentShift.shift_users.filter(
      (shiftUser) => shiftUser.needs_replacement
    );
    const currentUserInShift = currentShift.shift_users.some(
      (shiftUser) => shiftUser.id === currentUser.id
    );

    function replaceUserInShift(selected_user) {
      const shift_id = parseInt(currentShift.id, 10);
      dispatch(
        deleteShiftUser({
          userID: selected_user.id,
          shift_id,
        })
      ).then((result) => {
        if (result.status === "success") {
          dispatch(
            addShiftUser({
              shift_id,
              userID: currentUser.id,
              admin: false,
              needs_replacement: false,
            })
          ).then((next_result) => {
            if (next_result.status === "success") {
              dispatch(
                showNotification(`replaced user: ${selected_user.username}`)
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
              id="replace-users-button"
              variant="contained"
              color="primary"
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
              id="deactivated-replace-users-button"
              variant="contained"
              color="secondary"
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
          (shiftUser) => shiftUser.id === currentUser.id
        );
        if (!userHasAlreadyAskedForReplacement) {
          button = (
            <Tooltip title="Ask for someone to replace you. All users from the group associated to the Shift will be notified">
              <Button
                id="ask-for-replacement-button"
                variant="contained"
                color="primary"
                className={classes.replacementButton}
                onClick={() => {
                  const shift_id = parseInt(currentShift.id, 10);
                  const userID = parseInt(currentUser.id, 10);
                  dispatch(
                    updateShiftUser({
                      userID,
                      admin: false,
                      needs_replacement: true,
                      shift_id,
                    })
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
                onClick={handleChangeReplace}
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
      deleteShiftUser({ userID: currentUser.id, shift_id: shift.id })
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification(`left shift: ${shift.name}`));
      }
    });
  };
  let admins;
  let members;
  let participating;
  if (currentShift.name != null) {
    // create list names of non admin members
    admins = currentShift.shift_users
      .filter((user) => user.admin)
      .map((user) => `${userLabel(user)}`);
    members = currentShift.shift_users
      .filter((user) => !user.admin)
      .map((user) => `${userLabel(user)}`);
    participating = currentShift.shift_users
      .map((user) => user.id)
      .includes(currentUser.id);
  }
  let [shiftDateStartEnd, shiftTimeStartEnd] = [null, null];
  if (currentShift.name != null && dailyShiftStartEnd(currentShift)) {
    [shiftDateStartEnd, shiftTimeStartEnd] = dailyShiftStartEnd(currentShift);
  }
  let currentUserIsAdminOfShift = false;
  if (currentShift.name != null) {
    if (
      currentShift.shift_users.filter(
        (user) => user.id === currentUser.id && user.admin
      ).length > 0
    ) {
      currentUserIsAdminOfShift = true;
    }
  }

  let currentUserIsAdminOfGroup = false;
  if (currentShift.name != null) {
    if (
      currentShift.group.group_users.filter(
        (user) => user.id === currentUser.id && user.admin
      ).length > 0
    ) {
      currentUserIsAdminOfGroup = true;
    }
  }

  return (
    currentShift.name != null && (
      <div id="current_shift" className={classes.root}>
        <div className={classes.shift_content}>
          <div>
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
              Group: {currentShift.group.name}
            </h3>
            <div>
              <i id="current_shift_admins">{`\n Admins : ${admins.join(
                ", "
              )}`}</i>
            </div>
            <div>
              <i id="current_shift_members">{`\n Members : ${members.join(
                ", "
              )}`}</i>
            </div>
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
}

CurrentShiftMenu.propTypes = {
  currentShift: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    description: PropTypes.string,
    start_date: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.instanceOf(Date),
    ]),
    end_date: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.instanceOf(Date),
    ]),
    group: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      group_users: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          admin: PropTypes.bool,
        })
      ),
    }),
    shift_users: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        admin: PropTypes.bool,
      })
    ),
  }).isRequired,
};

export function CommentOnShift(resourceType) {
  const classes = useStyles();
  const { associatedResourceType } = resourceType;
  const { currentShift } = useSelector((state) => state.shift);

  return (
    currentShift.name != null && (
      <div id="current_shift_comment" className={classes.root}>
        <div className={classes.content}>
          <CommentList associatedResourceType={associatedResourceType} />
        </div>
      </div>
    )
  );
}

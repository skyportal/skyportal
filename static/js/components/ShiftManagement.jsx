import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import { makeStyles } from "@material-ui/core/styles";
import { showNotification } from "baselayer/components/Notifications";
import * as shiftActions from "../ducks/shift";
import { addShiftUser, deleteShiftUser } from "../ducks/shifts";

const useStyles = makeStyles(() => ({
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
    marginBottom: "1.5rem",
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
  },
  buttons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "right",
    // no gap
    gap: "0",
  },
}));

function CurrentShiftMenu() {
  const classes = useStyles();

  const { currentShift } = useSelector((state) => state.shift);
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();

  const deleteShift = (shift) => {
    dispatch(shiftActions.deleteShift(shift.id)).then((result) => {
      if (result.status === "success") {
        // dispatch an empty shift to clear the current shift
        dispatch({ type: "skyportal/CURRENT_SHIFT", data: {} });
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
        // dispatch currentShift adding the current user
        currentShift.users.push(currentUser);
        dispatch({ type: "skyportal/CURRENT_SHIFT", data: currentShift });
      }
    });
  };

  const leaveShift = (shift) => {
    dispatch(
      deleteShiftUser({ userID: currentUser.id, shift_id: shift.id })
    ).then((result) => {
      if (result.status === "success") {
        // dispatch currentShift without the current user
        currentShift.users = [...currentShift.users].filter(
          (user) => user.id !== currentUser.id
        );
        dispatch({ type: "skyportal/CURRENT_SHIFT", data: currentShift });
        dispatch(showNotification(`left shift: ${shift.name}`));
      }
    });
  };
  let members;
  let participating;
  if (currentShift.name != null) {
    members = currentShift.users.map(
      (user) => `${user.first_name} ${user.last_name}`
    );
    participating = currentShift.users
      .map((user) => user.id)
      .includes(currentUser.id);
  }

  return (
    currentShift.name != null && (
      <div id="current_shift" className={classes.content}>
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
          <i id="current_shift_members">{`\n Members : ${members.join(
            ","
          )}`}</i>
        </div>
        <div className={classes.buttons}>
          {!participating && (
            <Button id="join_button" onClick={() => joinShift(currentShift)}>
              Join
            </Button>
          )}
          {participating && (
            <Button id="leave_button" onClick={() => leaveShift(currentShift)}>
              Leave
            </Button>
          )}
          <Button id="delete_button" onClick={() => deleteShift(currentShift)}>
            Delete
          </Button>
        </div>
      </div>
    )
  );
}

export default CurrentShiftMenu;

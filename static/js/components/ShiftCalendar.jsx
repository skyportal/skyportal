import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { Calendar, momentLocalizer, Views } from "react-big-calendar";
import moment from "moment";
import "react-big-calendar/lib/css/react-big-calendar.css";
import { Button } from "@material-ui/core";
import { showNotification } from "baselayer/components/Notifications";
import PropTypes from "prop-types";
import * as shiftActions from "../ducks/shift";
import { addShiftUser, deleteShiftUser } from "../ducks/shifts";

/* eslint-disable no-alert */
/* eslint-disable react/prop-types */

const allViews = Object.keys(Views).map((k) => Views[k]);
let dispatch;
let currentUser;
const localizer = momentLocalizer(moment);
let groups;

function datestringToDate(shifts) {
  for (let i = 0; i < shifts.length; i += 1) {
    shifts[i].start_date = new Date(`${shifts[i].start_date}Z`);
    shifts[i].end_date = new Date(`${shifts[i].end_date}Z`);
  }
  return shifts;
}

async function handleSelectSlot({ start, end }) {
  const name = window.prompt("New Shift name");
  const description = window.prompt("New Shift description");
  const group_ids = groups.map((group) => `   ${group.name}: ${group.id}\n`);
  const group_id = await window.prompt(
    `Choose shift group ID : \n ${group_ids}`
  );
  const start_date = start.toISOString().replace("Z", "");
  const end_date = end.toISOString().replace("Z", "");
  dispatch(
    shiftActions.submitShift({
      name,
      description,
      start_date,
      end_date,
      group_id,
    })
  ).then((result) => {
    if (result.status === "success") {
      showNotification("Shift saved");
    }
  });
}

function Event({ event }) {
  const deleteShift = (shift) => {
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
        canSave: true,
      })
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification(`joined shift: ${shift.name}`));
      }
    });
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

  const members = event.users.map(
    (user) => `${user.first_name} ${user.last_name}`
  );
  const participating = event.users
    .map((user) => user.id)
    .includes(currentUser.id);
  return (
    <span>
      <strong>{event.name}</strong>
      {event.description && `: ${event.description}`}
      <i>{`\n Members : ${members.join(",")}`}</i>
      {!participating && (
        <Button id="join_button" onClick={() => joinShift(event)}>
          Join
        </Button>
      )}
      {participating && (
        <Button id="leave_button" onClick={() => leaveShift(event)}>
          Leave
        </Button>
      )}
      <Button id="delete_button" onClick={() => deleteShift(event)}>
        Delete
      </Button>
    </span>
  );
}

function MyCalendar({ shifts }) {
  shifts = datestringToDate(shifts);
  currentUser = useSelector((state) => state.profile);
  dispatch = useDispatch();
  groups = useSelector((state) => state.groups.userAccessible);
  return (
    <div>
      <Calendar
        events={shifts}
        views={allViews}
        step={60}
        defaultView={Views.WEEK}
        showMultiDayTimes
        localizer={localizer}
        style={{ height: "80vh", width: "40vw" }}
        components={{
          event: Event,
        }}
        startAccessor="start_date"
        endAccessor="end_date"
        titleAccessor="description"
        selectable
        onSelectSlot={handleSelectSlot}
        eventPropGetter={(event) => {
          let backgroundColor = "#0d98ba";
          if (event.users.map((user) => user.id).includes(currentUser.id)) {
            backgroundColor = "#0dba86";
          } else {
            backgroundColor = "#0d98ba";
          }
          return {
            style: {
              backgroundColor,
            },
          };
        }}
      />
    </div>
  );
}

MyCalendar.propTypes = {
  event: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    start_date: PropTypes.string.isRequired,
    end_date: PropTypes.string.isRequired,
    users: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        first_name: PropTypes.string,
        last_name: PropTypes.string,
      })
    ).isRequired,
  }).isRequired,

  shifts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      description: PropTypes.string,
      start_date: PropTypes.string,
      end_date: PropTypes.string,
      users: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          first_name: PropTypes.string,
          last_name: PropTypes.string,
        })
      ),
    }).isRequired
  ).isRequired,
};
export default MyCalendar;

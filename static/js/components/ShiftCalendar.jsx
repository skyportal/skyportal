import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { Calendar, momentLocalizer, Views } from "react-big-calendar";
import moment from "moment";
import "react-big-calendar/lib/css/react-big-calendar.css";
import { makeStyles } from "@material-ui/core/styles";
import { showNotification } from "baselayer/components/Notifications";
import PropTypes from "prop-types";
import * as shiftActions from "../ducks/shift";

const useStyles = makeStyles((theme) => ({
  shiftmenu: {
      marginBottom:'1.5rem'
  },
  shiftinfo: {
      marginLeft:'1rem',
      paddingTop:'1rem'
  },
  members: {
      marginLeft:'1rem'
  }
}));

const allViews = Object.keys(Views).map((k) => Views[k]);
let dispatch;
let currentUser;
const localizer = momentLocalizer(moment);
let groups;

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

function setCurrentShift(event) {
  dispatch({ type: "skyportal/CURRENT_SHIFT", data: event });
}

function Event({ event }) {
  return (
    <span>
      <strong>{event.name}</strong>
    </span>
  );
}

function MyCalendar({ shifts }) {
  currentUser = useSelector((state) => state.profile);
  dispatch = useDispatch();
  groups = useSelector((state) => state.groups.userAccessible);
  console.log(shifts);
  return (
      <Calendar
        events={shifts}
        views={allViews}
        step={60}
        defaultView={Views.WEEK}
        showMultiDayTimes
        localizer={localizer}
        style={{ height: "70vh", width: "100%" }}
        components={{
          event: Event,
        }}
        startAccessor="start_date"
        endAccessor="end_date"
        titleAccessor="name"
        selectable
        onSelectEvent={(event) => setCurrentShift(event)}
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
  );
}

MyCalendar.propTypes = {
  shifts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      description: PropTypes.string,
      start_date: PropTypes.instanceOf(Date),
      end_date: PropTypes.instanceOf(Date),
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

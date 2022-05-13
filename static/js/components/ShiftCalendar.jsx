import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { Calendar, momentLocalizer, Views } from "react-big-calendar";
import moment from "moment";
import "react-big-calendar/lib/css/react-big-calendar.css";
import { showNotification } from "baselayer/components/Notifications";
import { CircularProgress } from "@material-ui/core";
import PropTypes from "prop-types";
import * as shiftActions from "../ducks/shift";

/* eslint-disable react/prop-types */

const allViews = Object.keys(Views).map((k) => Views[k]);
let dispatch;
let currentUser;
const localizer = momentLocalizer(moment);
let groups;

function isDailyShift(shiftName) {
  const regex = /\d+\/\d+$/;
  return regex.test(shiftName);
}

async function handleSelectSlot({ start, end }) {
  const name = window.prompt("New Shift name");
  if (name !== "" && name != null && !isDailyShift(name)) {
    const description = window.prompt("New Shift description");
    if (description === "" || description != null) {
      const group_ids = groups
        .map((group) => `   ${group.name}: ${group.id}`)
        .join("\n");
      let group_id = await window.prompt(
        `Choose shift group ID : \n${group_ids}`
      );
      if (group_id === "") {
        group_id = groups[0].id;
        dispatch(
          showNotification(
            `Shift group not selected, defaulting to: ${groups[0].name}`,
            "warning"
          )
        );
      }
      if (group_id != null) {
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
            dispatch(showNotification("Shift saved"));
          }
        });
      }
    }
  } else if (name === "") {
    dispatch(showNotification("Shift not created, no name given", "error"));
  } else if (isDailyShift(name)) {
    dispatch(
      showNotification(
        'Shift not created, invalid name (dont use "number/number" at end of name)',
        "error"
      )
    );
  }
}

function setCurrentShift(event) {
  dispatch({ type: "skyportal/CURRENT_SHIFT", data: event });
  dispatch({ type: "skyportal/CURRENT_SHIFT_SELECTED_USERS", data: [] });
}

function Event({ event }) {
  return (
    <div id={`event_${event.id}`}>
      <span>
        <strong>{event.name}</strong>
        <p>{event.group.name}</p>
      </span>
    </div>
  );
}

function MyCalendar({ events, currentShift }) {
  currentUser = useSelector((state) => state.profile);
  dispatch = useDispatch();
  groups = useSelector((state) => state.groups.userAccessible);
  const [defaultDate, setDefaultDate] = React.useState();

  if (currentShift && !defaultDate) {
    if (currentShift.start_date) {
      if (typeof currentShift.start_date === "string") {
        setDefaultDate(new Date(`${currentShift.start_date}Z`));
      } else {
        setDefaultDate(new Date(currentShift.start_date.getTime()));
      }
    }
  } else if (!defaultDate) {
    setDefaultDate(new Date());
  }

  const handleNavigate = (date) => {
    setDefaultDate(moment(date).toDate());
  };

  return (
    <div>
      {!events ? (
        <CircularProgress />
      ) : (
        <Calendar
          events={events}
          date={defaultDate}
          onNavigate={handleNavigate}
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
            if (
              event.shift_users.map((user) => user.id).includes(currentUser.id)
            ) {
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
      )}
    </div>
  );
}

MyCalendar.propTypes = {
  events: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      description: PropTypes.string,
      start_date: PropTypes.instanceOf(Date),
      end_date: PropTypes.instanceOf(Date),
      shift_users: PropTypes.arrayOf(
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

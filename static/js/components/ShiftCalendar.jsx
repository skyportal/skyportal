import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { Calendar, momentLocalizer, Views } from "react-big-calendar";
import "react-big-calendar/lib/css/react-big-calendar.css";
import moment from "moment";
import {
  CircularProgress,
  FormControlLabel,
  FormGroup,
  Switch,
  Tooltip,
} from "@mui/material";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import GroupsSelect from "./group/GroupsSelect";
import * as shiftActions from "../ducks/shift";

/* eslint-disable react/prop-types */

const allViews = Object.keys(Views).map((k) => Views[k]);
let dispatch;
let currentUser;
const localizer = momentLocalizer(moment);
let groups;

const useStyles = makeStyles((theme) => ({
  content: {
    padding: theme.spacing(2),
    paddingBottom: "0",
  },
  typography: {
    padding: theme.spacing(2),
  },
  pref: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
    height: "5rem",
  },
  optionsHeader: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "10px",
    width: "100%",
    height: "4rem",
  },
  options: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
    width: "100%",
    height: "4rem",
  },
  help: {
    display: "flex",
    justifyContent: "right",
    alignItems: "center",
  },
  tooltip: {
    maxWidth: "60rem",
    fontSize: "1.2rem",
  },
  tooltipContent: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "100%",
  },
  legend: {
    width: "100%",
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
  },
  circle: {
    borderRadius: "50%",
    width: "25px",
    height: "25px",
    display: "inline-block",
  },
}));

const red = "#c0392b";
const orange = "#e46828";
const green = "#359d73";
const grey = "#95a5a6";
const blue = "#357ec7";

function isDailyShift(shiftName) {
  const regex = /\d+\/\d+$/;
  return regex.test(shiftName);
}

async function handleSelectSlot({ start, end }) {
  const name = window.prompt("New Shift name");
  if (name !== "" && name !== null && !isDailyShift(name)) {
    const description = window.prompt("New Shift description");
    if (description === "" || description !== null) {
      const group_ids = groups
        .map((group) => `   ${group.name}: ${group.id}`)
        .join("\n");
      let group_id = await window.prompt(
        `Choose shift group ID : \n${group_ids}`,
      );
      if (group_id === "") {
        group_id = groups[0].id;
        dispatch(
          showNotification(
            `Shift group not selected, defaulting to: ${groups[0].name}`,
            "warning",
          ),
        );
      }
      if (groups.find((group) => group.id === parseInt(group_id, 10))) {
        const start_date = start.toISOString().replace("Z", "");
        const end_date = end.toISOString().replace("Z", "");
        let required_users_number = window.prompt("Number of users");
        if (required_users_number !== "") {
          required_users_number = parseInt(required_users_number, 10);
        }
        if (!Number.isNaN(required_users_number)) {
          dispatch(
            shiftActions.submitShift({
              name,
              description,
              start_date,
              end_date,
              group_id,
              required_users_number: parseInt(required_users_number, 10),
            }),
          ).then((result) => {
            if (result.status === "success") {
              dispatch(showNotification("Shift saved"));
              const new_shift_id = result?.data?.id;
              if (new_shift_id) {
                dispatch(shiftActions.fetchShift(new_shift_id));
              }
            }
          });
        } else {
          dispatch(
            showNotification(
              "Shift not created. Required users number needs to be a number",
              "error",
            ),
          );
        }
      } else {
        dispatch(
          showNotification("Shift not created, Incorrect Group ID.", "error"),
        );
      }
    }
  } else if (name === "") {
    dispatch(showNotification("Shift not created, no name given", "error"));
  } else if (isDailyShift(name)) {
    dispatch(
      showNotification(
        'Shift not created, invalid name (dont use "number/number" at end of name)',
        "error",
      ),
    );
  }
}

function setCurrentShift({ event, setShow }) {
  dispatch(shiftActions.fetchShift(event?.id));
  dispatch({ type: "skyportal/CURRENT_SHIFT_SELECTED_USERS", data: [] });
  dispatch(
    shiftActions.getShiftsSummary({
      shiftID: event.id,
    }),
  );
  setShow(false);
}

function MyCalendar({ events, currentShift, setShow }) {
  const classes = useStyles();
  currentUser = useSelector((state) => state.profile);
  dispatch = useDispatch();
  groups = useSelector((state) => state.groups.userAccessible);
  const [defaultDate, setDefaultDate] = React.useState();
  const [showAllShifts, setShowAllShifts] = React.useState(false);
  const [sortByGroups, setSortByGroups] = React.useState(false);
  const [selectedGroups, setSelectedGroups] = React.useState([]);

  useEffect(() => {
    if (groups[0]) {
      setSelectedGroups([groups[0]]);
    }
  }, [groups]);

  if (!showAllShifts) {
    events = events.filter((event) =>
      (event.shift_users_ids || []).includes(currentUser.id),
    );
  }
  if (sortByGroups) {
    events = events.filter(
      (event) =>
        selectedGroups.filter((group) => group.id === event.group_id)?.length >
        0,
    );
  }

  function Event({ event }) {
    // find the group in the groups array which id matches the event.group_id
    const group_name =
      groups.find((group) => group.id === event.group_id)?.name || "";
    return (
      <div id={`event_${event.id}`}>
        <span>
          <strong>{event.name}</strong>
          <p>{group_name}</p>
        </span>
      </div>
    );
  }

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

  const shiftStatus = (event) => {
    const currentUserInShift = (event.shift_users_ids || []).includes(
      currentUser.id,
    );
    const style = {
      background: blue,
    };
    if (event?.end_date < new Date()) {
      style.background = grey;
    } else if (
      (event.shift_users_ids || []).length < event?.required_users_number &&
      event?.end_date > new Date()
    ) {
      // if the shift will happen in less than 72 hours but more than 24h is shows as orange, less than 24hours shows as red
      // otherwise, is grey
      if (
        event.start_date.getTime() - new Date().getTime() <=
          72 * 60 * 60 * 1000 &&
        event.start_date.getTime() - new Date().getTime() > 24 * 60 * 60 * 1000
      ) {
        style.background = orange;
      } else if (
        event.start_date.getTime() - new Date().getTime() <=
        24 * 60 * 60 * 1000
      ) {
        style.background = red;
      }
    }
    if (currentUserInShift && style.background === blue) {
      style.background = green;
    } else if (
      currentUserInShift &&
      style.background !== grey &&
      style.background !== blue
    ) {
      style.background = `repeating-linear-gradient(45deg, ${green}, ${green} 10px, ${style.background} 10px, ${style.background} 20px)`;
    }
    if (event.id === currentShift.id) {
      style.borderColor = "black";
      style.borderWidth = "2px";
    }
    return {
      style,
    };
  };

  const handleChangeShowAllShifts = () => {
    setShowAllShifts(!showAllShifts);
  };

  const handleChangeSortByGroups = () => {
    setSortByGroups(!sortByGroups);
  };

  const Title = () => (
    <div className={classes.tooltipContent}>
      <div className={classes.legend}>
        <div style={{ background: green }} className={classes.circle} />
        <p> Shift that you are a member of</p>
      </div>
      <div className={classes.legend}>
        <div style={{ background: grey }} className={classes.circle} />
        <p> Shift that already happened</p>
      </div>
      <div className={classes.legend}>
        <div style={{ background: blue }} className={classes.circle} />
        <p> Shift that did not happen yet, or is happening right now</p>
      </div>
      <div className={classes.legend}>
        <div style={{ background: red }} className={classes.circle} />
        <p>
          {" "}
          Shift will happen in less than 24 hours, and the required number of
          users is not reached
        </p>
      </div>
      <div className={classes.legend}>
        <div style={{ background: orange }} className={classes.circle} />
        <p>
          {" "}
          Shift will happen in less then 72 hours but more than 24 hours, and
          the required number of users is not reached
        </p>
      </div>
      <div className={classes.legend}>
        <div
          style={{
            background: `repeating-linear-gradient(45deg, ${green}, ${green} 17.5px, ${red} 17.5px, ${red} 30px)`,
          }}
          className={classes.circle}
        />
        <div
          style={{
            background: `repeating-linear-gradient(45deg, ${green}, ${green} 17.5px, ${orange} 17.5px, ${orange} 30px)`,
          }}
          className={classes.circle}
        />
        <p>
          {" "}
          Member of the shift, but it will happen in less than 72 hours <br />{" "}
          and did not reach the required number of users
        </p>
      </div>
    </div>
  );
  const ShiftToolTip = () => (
    <Tooltip
      title={Title()}
      placement="top"
      classes={{ tooltip: classes.tooltip }}
    >
      <HelpOutlineOutlinedIcon />
    </Tooltip>
  );

  return (
    <div>
      {!events ? (
        <CircularProgress />
      ) : (
        <div className={classes.content}>
          <Calendar
            events={events}
            date={defaultDate}
            onNavigate={handleNavigate}
            views={allViews}
            step={60}
            defaultView={Views.WEEK}
            showMultiDayTimes
            localizer={localizer}
            style={{ height: "77vh", width: "100%" }}
            components={{
              event: Event,
            }}
            startAccessor="start_date"
            endAccessor="end_date"
            titleAccessor="name"
            selectable
            onSelectEvent={(event) => setCurrentShift({ event, setShow })}
            onSelectSlot={handleSelectSlot}
            eventPropGetter={(event) => shiftStatus(event)}
          />
          <div className={classes.optionsHeader}>
            <div className={classes.options}>
              <div className={classes.pref}>
                <FormGroup row>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showAllShifts === true}
                        name="show_all_shifts"
                        onChange={() => {
                          handleChangeShowAllShifts();
                        }}
                      />
                    }
                    label="Show All Shifts"
                  />
                </FormGroup>
              </div>

              <div className={classes.pref}>
                <FormGroup row>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={sortByGroups === true}
                        name="sort_by_groups"
                        onChange={() => {
                          handleChangeSortByGroups();
                        }}
                      />
                    }
                    label="Sort By Group(s)"
                  />
                </FormGroup>
                {sortByGroups === true && (
                  <GroupsSelect
                    selectedGroups={selectedGroups}
                    setSelectedGroups={setSelectedGroups}
                  />
                )}
              </div>
            </div>
            <div className={classes.help}>
              <ShiftToolTip />
            </div>
          </div>
        </div>
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
      reauired_users_number: PropTypes.number,
      shift_users: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          first_name: PropTypes.string,
          last_name: PropTypes.string,
          affiliations: PropTypes.arrayOf(PropTypes.string),
        }),
      ),
    }).isRequired,
  ).isRequired,
};
export default MyCalendar;

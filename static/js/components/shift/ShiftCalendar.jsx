import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { Calendar, momentLocalizer, Views } from "react-big-calendar";
import "react-big-calendar/lib/css/react-big-calendar.css";
import moment from "moment";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import makeStyles from "@mui/styles/makeStyles";
import GroupsSelect from "../group/GroupsSelect";
import * as shiftsActions from "../../ducks/shifts";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

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
const transparent = "rgba(53,126,199,0.6)";

function MyCalendar({
  events,
  setShow,
  preSelectedRange,
  setPreSelectedRange,
}) {
  const classes = useStyles();
  const currentShift = useSelector((state) => state.shifts.currentShift);
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

    const match = event.name.match(/^(.*)\s+(\d+\/\d+)$/);
    const baseName = match ? match[1].trim() : event.name;
    const counter = match ? match[2] : null;
    return (
      <Box id={`event_${event.id}`}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.6, mb: 1 }}>
          <Typography variant="body1" fontWeight="bold">
            {baseName}
          </Typography>
          {counter !== null && (
            <Typography variant="body2">{counter}</Typography>
          )}
        </Box>
        <Typography variant="body2" sx={{ mb: 0.2 }}>
          {group_name}
        </Typography>
        <Typography variant="body2">
          Users: {(event.shift_users_ids || []).length}
          {event.required_users_number ? `/${event.required_users_number}` : ""}
        </Typography>
      </Box>
    );
  }

  if (!defaultDate) {
    setDefaultDate(
      currentShift?.start_date
        ? new Date(`${currentShift.start_date}Z`)
        : new Date(),
    );
  }

  const handleNavigate = (date) => {
    setDefaultDate(moment(date).toDate());
  };

  const shiftStatus = (event) => {
    if (event.isPreview) {
      return {
        style: {
          backgroundColor: "rgba(0,0,0,0.3)",
          border: "dashed gray",
        },
      };
    }
    const currentUserInShift = (event.shift_users_ids || []).includes(
      currentUser.id,
    );
    const style = {
      background:
        (event.shift_users_ids || []).length === 0 ? transparent : blue,
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
            events={[...events, preSelectedRange]}
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
            formats={{
              timeGutterFormat: (date) => {
                const utcHour = date.getUTCHours().toString().padStart(2, "0");
                const localHour = localizer.format(date, "HH");
                return `${localHour}h (UTC ${utcHour}h)`;
              },
            }}
            startAccessor="start_date"
            endAccessor="end_date"
            titleAccessor="name"
            selectable
            onSelectEvent={(event) => {
              if (event.id === currentShift.id) return;
              if (event.isPreview) {
                setPreSelectedRange(null);
                return;
              }
              dispatch(shiftsActions.setCurrentShift(event.id));
              dispatch(
                shiftsActions.getShiftsSummary({
                  shiftID: event.id,
                }),
              );
              setShow("manage shift");
            }}
            onSelectSlot={(slotInfo) => {
              if (slotInfo) {
                setPreSelectedRange({
                  id: "__preview__",
                  start_date: slotInfo.start,
                  end_date: slotInfo.end,
                  name: "- Preview -",
                  isPreview: true,
                });
                setShow("new shift");
              }
            }}
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
      required_users_number: PropTypes.number,
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
  setShow: PropTypes.func.isRequired,
  preSelectedRange: PropTypes.shape({
    id: PropTypes.string,
    start_date: PropTypes.instanceOf(Date),
    end_date: PropTypes.instanceOf(Date),
    isPreview: PropTypes.bool,
  }),
  setPreSelectedRange: PropTypes.func.isRequired,
};
export default MyCalendar;

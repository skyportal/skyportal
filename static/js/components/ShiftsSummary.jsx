import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";
import Form from "@rjsf/material-ui";
import { showNotification } from "baselayer/components/Notifications";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import { Collapse } from "@material-ui/core";
import { ExpandMore, ExpandLess } from "@material-ui/icons";
import * as shiftActions from "../ducks/shift";

const useStyles = makeStyles((theme) => ({
  root: {
    marginBottom: theme.spacing(2),
  },
  nestedList: {
    paddingLeft: theme.spacing(4),
  },
  link: {
    fontSize: "1.5rem",
    color: "blue",
  },
  info: {
    margin: "0",
  },
}));

const ShiftsSummary = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [selectedGCN, setSelectedGCN] = useState(null);
  // return a react json schema form where the user can select a start date and end date, and then click submit to get  json document that summarizes the activity during shifts between the start and end dates
  const shiftsSummary = useSelector((state) => state.shift.shiftsSummary);

  const defaultStartDate = dayjs()
    .subtract(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const shiftFormSchema = {
    type: "object",
    properties: {
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date (Local Time)",
        default: defaultStartDate,
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date (Local Time)",
        default: defaultEndDate,
      },
    },
  };

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    // if the period is over 4 weeks, then error
    if (dayjs(formData.end_date).diff(dayjs(formData.start_date), "week") > 4) {
      errors.end_date.addError("Period must be less than 4 weeks, please fix.");
    }
    return errors;
  }

  const handleSubmit = async ({ formData }) => {
    formData.start_date = formData.start_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.end_date = formData.end_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    if (formData.end_date && formData.start_date) {
      dispatch(
        shiftActions.getShiftsSummary({
          start_date: formData.start_date,
          end_date: formData.end_date,
        })
      );
      showNotification("Shifts Summary", "Shifts Summary", "success");
    }
  };

  function shiftInfo(shift) {
    // returns a 2 line text with :
    // 1. shift start date and end date (UTC)
    // 2. shift members (admin and non-admin)
    return (
      <div className={classes.info}>
        <p className={classes.info}>
          {`${shift.start_date} UTC - ${shift.end_date} UTC`}
        </p>
        <p className={classes.info}>
          {`Members: ${shift.shift_users
            .map(
              (member) =>
                `${member.username} ${
                  member.first_name && member.last_name
                    ? `(${member.first_name}  ${member.last_name})`
                    : null
                }`
            )
            .join(", ")}`}
        </p>
      </div>
    );
  }

  function displayShiftsList(shifts) {
    return (
      <List className={classes.root}>
        <h2>Shifts:</h2>
        {shifts.map((shift) => (
          <ListItem key={shift.id}>
            <ListItemText
              primary={
                <a href={`/shifts/${shift.id}`} className={classes.link}>
                  {shift.name}
                </a>
              }
              secondary={shiftInfo(shift)}
            />
          </ListItem>
        ))}
      </List>
    );
  }

  function gcnInfo(gcn, shifts) {
    return (
      <div className={classes.info}>
        <p
          className={classes.info}
        >{`Sources in GCN: ${gcn.sources.length}`}</p>
        <p className={classes.info}>{`discovered during shift: ${
          shifts.find((shift) => shift.id === gcn.shift_id).name
        }`}</p>
      </div>
    );
  }

  function displaySourcesInGCN(sources) {
    return (
      <List className={classes.nestedList}>
        {sources.map((source) => (
          <ListItem key={source.id}>
            <ListItemText
              primary={
                <a href={`/source/${source.id}`}>{`Source: ${source.id}`}</a>
              }
              secondary={`ra: ${source.ra}, dec: ${
                source.dec
              }, last detected: ${source.last_detected_at.replace(
                "+00:00",
                " UTC"
              )}`}
            />
          </ListItem>
        ))}
      </List>
    );
  }

  function displayShiftsGCN(shifts, gcns) {
    return (
      <List className={classes.root}>
        <h2>GCN Events:</h2>
        {gcns.map((gcn) => (
          <div key={gcn.id}>
            <ListItem
              key={gcn.id}
              onClick={() => {
                if (gcn.sources.length > 0) {
                  if (selectedGCN === gcn.id) {
                    setSelectedGCN(null);
                  } else {
                    setSelectedGCN(gcn.id);
                  }
                }
              }}
            >
              <ListItemText
                primary={
                  <a
                    href={`/gcn_events/${gcn.dateobs}`}
                    className={classes.link}
                  >
                    {gcn.dateobs}
                  </a>
                }
                secondary={gcnInfo(gcn, shifts)}
              />
              {gcn.sources.length > 0 &&
                (selectedGCN === gcn.id ? <ExpandLess /> : <ExpandMore />)}
            </ListItem>
            <Collapse in={selectedGCN === gcn.id} timeout="auto" unmountOnExit>
              {displaySourcesInGCN(gcn.sources)}
            </Collapse>
          </div>
        ))}
      </List>
    );
  }

  return (
    <div>
      <Form
        schema={shiftFormSchema}
        onSubmit={handleSubmit}
        // eslint-disable-next-line react/jsx-no-bind
        validate={validate}
        liveValidate
      />
      {console.log(shiftsSummary)}
      {shiftsSummary?.shifts?.total > 1 &&
        displayShiftsList(shiftsSummary.shifts.data)}
      {shiftsSummary?.gcns &&
        displayShiftsGCN(shiftsSummary.shifts.data, shiftsSummary.gcns.data)}
    </div>
  );
};

export default ShiftsSummary;

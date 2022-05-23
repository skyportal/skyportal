import React from "react";
import { useSelector, useDispatch } from "react-redux";
import dayjs from "dayjs";
import Form from "@rjsf/material-ui";
import { showNotification } from "baselayer/components/Notifications";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import * as shiftActions from "../ducks/shift";

const ShiftsSummary = () => {
  const dispatch = useDispatch();
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

  const displayShiftsList = (shifts) => (
    <List>
      <h2>Shifts:</h2>
      {shifts.map((shift) => (
        <ListItem key={shift.id}>
          <ListItemText
            primary={`${shift.name}`}
            secondary={`${shift.start_date} - ${shift.end_date}`}
          />
          <p>
            {" "}
            Members :{" "}
            {shift.shift_users.map((user) => user.username).join(", ")}
          </p>
        </ListItem>
      ))}
    </List>
  );

  const displayShiftsGCN = (shifts, gcns) => {
    <List>
      <h2>GCN Events:</h2>
      {gcns.map((gcn) => (
        <ListItem key={gcn.id}>
          <ListItemText
            primary={`${gcn.dateobs}`}
            secondary={`${gcn.start_date} - ${gcn.end_date}`}
          />
          {shifts.length > 1 ? (
            <p>
              {" "}
              Shift : {shifts.find((shift) => shift.id === gcn.shift_id).name}
            </p>
          ) : null}
        </ListItem>
      ))}
    </List>;
  };
  return (
    <div>
      <Form
        schema={shiftFormSchema}
        onSubmit={handleSubmit}
        // eslint-disable-next-line react/jsx-no-bind
        validate={validate}
        liveValidate
      />
      {shiftsSummary?.shifts?.total > 1 &&
        displayShiftsList(shiftsSummary.shifts.data)}
      {shiftsSummary?.gcns &&
        displayShiftsGCN(shiftsSummary.shifts.data, shiftsSummary.gcns.data)}
    </div>
  );
};

export default ShiftsSummary;

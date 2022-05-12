import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Form from "@rjsf/material-ui";
import { showNotification } from "baselayer/components/Notifications";
import * as shiftActions from "../ducks/shift";

const ShiftsSummary = () => {
  const dispatch = useDispatch();
  // return a react json schema form where the user can select a start date and end date, and then click submit to get  json document that summarizes the activity during shifts between the start and end dates
  const shiftsSummary = useSelector((state) => state.shift.shiftsSummary);

  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
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
    required: ["start_date", "end_date"],
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
    console.log("formData", formData);
    formData.start_date = formData.start_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.end_date = formData.end_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    console.log(formData.start_date);
    console.log(formData.end_date);
    dispatch(shiftActions.getShiftsSummary(formData));
    showNotification("Shifts Summary", "Shifts Summary", "success");
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
      {shiftsSummary && <div>{shiftsSummary}</div>}
    </div>
  );
};

export default ShiftsSummary;

import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { submitShift } from "../ducks/shift";
import { fetchShifts } from "../ducks/shifts";

dayjs.extend(utc);

const NewShift = () => {
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();

  const nowDate = new Date();
  const defaultStartDate = new Date();
  const defaultEndDate = new Date();
  defaultEndDate.setDate(defaultStartDate.getDate() + 1);

  if (!groups) {
    return <CircularProgress />;
  }

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitShift(formData));
    if (result.status === "success") {
      dispatch(showNotification("Shift saved"));
      dispatch(fetchShifts());
    }
  };

  function validate(formData, errors) {
    if (nowDate > formData.end_date) {
      errors.end_date.addError(
        "End date must be after current date, please fix."
      );
    }
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    return errors;
  }

  const shiftFormSchema = {
    type: "object",
    properties: {
      group_id: {
        type: "integer",
        oneOf: groups.map((group) => ({
          enum: [group.id],
          title: `${group.name}`,
        })),
        title: "Group",
        default: groups[0]?.id,
      },
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date UTC",
        default: dayjs.utc(defaultStartDate).format("YYYY-MM-DDTHH:mm:ssZ"),
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date UTC",
        default: dayjs.utc(defaultEndDate).format("YYYY-MM-DDTHH:mm:ssZ"),
      },
      name: {
        type: "string",
        title: "Shift name (i.e. the Night Shift)",
      },
    },
    required: ["group_id", "start_date", "end_date"],
  };

  return (
    <Form
      schema={shiftFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
    />
  );
};

export default NewShift;

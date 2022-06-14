import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import CircularProgress from "@mui/material/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { submitShift } from "../ducks/shift";
import { fetchShifts } from "../ducks/shifts";

dayjs.extend(utc);

function isDailyShift(shiftName) {
  const regex = /\d+\/\d+$/;
  return regex.test(shiftName);
}

const NewShift = () => {
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();
  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  if (!groups) {
    return <CircularProgress />;
  }

  const handleSubmit = async ({ formData }) => {
    if (!formData.repeatsDaily) {
      formData.start_date = formData.start_date
        .replace("+00:00", "")
        .replace(".000Z", "");
      formData.end_date = formData.end_date
        .replace("+00:00", "")
        .replace(".000Z", "");
      delete formData.repeatsDaily;
      const result = await dispatch(submitShift(formData));
      if (result.status === "success") {
        dispatch(showNotification("Shift saved"));
        dispatch(fetchShifts());
      }
    } else {
      delete formData.repeatsDaily;
      const startDate = dayjs(formData.start_date).utc();
      const endDate = dayjs(formData.end_date).utc();
      const days = endDate.diff(startDate, "days");
      for (let i = 0; i <= days; i += 1) {
        const newFormData = { ...formData };
        newFormData.name = `${newFormData.name} ${i}/${days}`;
        newFormData.start_date = startDate
          .add(i, "day")
          .format("YYYY-MM-DDTHH:mm:ssZ")
          .replace("+00:00", "")
          .replace(".000Z", "");
        newFormData.end_date = endDate
          .subtract(days - i, "day")
          .format("YYYY-MM-DDTHH:mm:ssZ")
          .replace("+00:00", "")
          .replace(".000Z", "");
        const result = dispatch(submitShift(newFormData));
        if (result.status === "success") {
          dispatch(showNotification("Shift saved"));
          dispatch(fetchShifts());
        }
      }
    }
  };

  function validate(formData, errors) {
    if (isDailyShift(formData.name)) {
      errors.name.addError(
        'Shift name cannot contain "number/number" at the end of the name, please fix.'
      );
    }
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

  const uiSchema = {
    repeatsDaily: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
  };

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
      name: {
        type: "string",
        title: "Shift name (ie. the Night Shift)",
      },
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
      required_users_number: {
        type: "integer",
        title: "Number of users required in the shift (optional)",
      },
      description: {
        type: "string",
        title: "Shift's description",
      },
      repeatsDaily: {
        type: "boolean",
        title: "Do you want to create daily shifts over the selected period ?",
        description:
          "If checked, shifts will be created for each day between start and end date, each of them starting at the start time and ending at the end time.",
      },
    },
    required: ["group_id", "name", "start_date", "end_date"],
  };

  return (
    <Form
      schema={shiftFormSchema}
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
      liveValidate
    />
  );
};

export default NewShift;

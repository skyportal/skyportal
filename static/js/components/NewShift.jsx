import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
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

  const nowDate = dayjs().local().format("YYYY-MM-DDTHH:mm:ss");
  const defaultStartDate = dayjs().local().format("YYYY-MM-DDTHH:mm:ss");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .local()
    .format("YYYY-MM-DDTHH:mm:ss");
  const timezoneString = dayjs()
    .local()
    .format("YYYY-MM-DDTHH:mm:ssZ")
    .slice(-6);

  const nowDateUTC = dayjs
    .utc()
    .utcOffset(0, true)
    .format("YYYY-MM-DDTHH:mm:ss");
  const defaultStartDateUTC = dayjs
    .utc()
    .utcOffset(0, true)
    .format("YYYY-MM-DDTHH:mm:ss");
  const defaultEndDateUTC = dayjs
    .utc()
    .add(1, "day")
    .utcOffset(0, true)
    .format("YYYY-MM-DDTHH:mm:ss");

  if (!groups) {
    return <CircularProgress />;
  }

  const handleSubmit = async ({ formData }) => {
    const { localTime } = formData;
    delete formData.localTime;

    if (!formData.repeatsDaily) {
      if (localTime === "local") {
        formData.start_date = dayjs(
          formData.start_date_local.concat("", timezoneString)
        )
          .utc()
          .format("YYYY-MM-DDTHH:mm:ss")
          .replace("+00:00", "")
          .replace(".000Z", "");
        formData.end_date = dayjs(
          formData.end_date_local.concat("", timezoneString)
        )
          .utc()
          .format("YYYY-MM-DDTHH:mm:ss")
          .replace("+00:00", "")
          .replace(".000Z", "");
      } else if (localTime === "UTC") {
        formData.start_date = formData.start_date_utc;
        formData.end_date = formData.end_date_utc;
      }
      delete formData.start_date_local;
      delete formData.end_date_local;
      delete formData.start_date_utc;
      delete formData.end_date_utc;
      delete formData.repeatsDaily;
      const result = await dispatch(submitShift(formData));
      if (result.status === "success") {
        dispatch(showNotification("Shift saved"));
        dispatch(fetchShifts());
      }
    } else {
      delete formData.repeatsDaily;

      if (localTime === "local") {
        formData.start_date = dayjs(
          formData.start_date_local.concat("", timezoneString)
        )
          .utc()
          .format("YYYY-MM-DDTHH:mm:ss")
          .replace("+00:00", "")
          .replace(".000Z", "");
        formData.end_date = dayjs(
          formData.end_date_local.concat("", timezoneString)
        )
          .utc()
          .format("YYYY-MM-DDTHH:mm:ss")
          .replace("+00:00", "")
          .replace(".000Z", "");
      } else if (localTime === "UTC") {
        formData.start_date = formData.start_date_utc;
        formData.end_date = formData.end_date_utc;
      }

      delete formData.start_date_local;
      delete formData.end_date_local;
      delete formData.start_date_utc;
      delete formData.end_date_utc;

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
    if (formData.localTime === "local") {
      if (nowDate > formData.end_date_local) {
        errors.end_date_local.addError(
          "End date must be after current date, please fix."
        );
      }
      if (formData.start_date_local > formData.end_date_local) {
        errors.start_date_local.addError(
          "Start date must be before end date, please fix."
        );
      }
    } else if (formData.localTime === "UTC") {
      if (nowDateUTC > formData.end_date_utc) {
        errors.end_date_utc.addError(
          "End date must be after current date, please fix."
        );
      }
      if (formData.start_date_utc > formData.end_date_utc) {
        errors.start_date_utc.addError(
          "Start date must be before end date, please fix."
        );
      }
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
      localTime: {
        type: "string",
        oneOf: [
          { enum: ["local"], title: "Local Time" },
          { enum: ["UTC"], title: "UTC Time" },
        ],
        default: "local",
        title: "Use local or UTC time?",
      },
    },
    required: ["group_id", "name"],
    dependencies: {
      localTime: {
        oneOf: [
          {
            properties: {
              localTime: {
                enum: ["local"],
              },
              start_date_local: {
                type: "string",
                title: "Start Date (Local Time)",
                default: defaultStartDate,
              },
              end_date_local: {
                type: "string",
                title: "End Date (Local Time)",
                default: defaultEndDate,
              },
            },
          },
          {
            properties: {
              localTime: {
                enum: ["UTC"],
              },
              start_date_utc: {
                type: "string",
                title: "Start Date (UTC Time)",
                default: defaultStartDateUTC,
              },
              end_date_utc: {
                type: "string",
                title: "End Date (UTC Time)",
                default: defaultEndDateUTC,
              },
            },
          },
        ],
      },
    },
  };

  return (
    <Form
      schema={shiftFormSchema}
      validator={validator}
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      customValidate={validate}
      liveValidate
    />
  );
};

export default NewShift;

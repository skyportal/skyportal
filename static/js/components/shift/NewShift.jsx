import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { fetchShift, submitShift } from "../../ducks/shift";

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

  if (!groups || groups?.length === 0) {
    return <CircularProgress />;
  }

  const handleSubmit = async ({ formData }) => {
    const { localTime, divide } = formData;
    delete formData.localTime;
    delete formData.divide;

    if (localTime === "local") {
      formData.start_date = dayjs(
        formData.start_date_local.concat("", timezoneString),
      )
        .utc()
        .format("YYYY-MM-DDTHH:mm:ss")
        .replace("+00:00", "")
        .replace(".000Z", "");
      formData.end_date = dayjs(
        formData.end_date_local.concat("", timezoneString),
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

    const startDate = dayjs(formData.start_date);
    const endDate = dayjs(formData.end_date);

    let days = 0;
    let weeks = 0;
    switch (divide) {
      case "Don't divide, just create one shift":
        dispatch(submitShift(formData)).then((response) => {
          if (response.status === "success") {
            dispatch(showNotification("Shift saved"));
            const new_shift_id = response?.data?.id;
            if (new_shift_id) {
              dispatch(fetchShift(new_shift_id));
            }
          }
        });
        break;
      case "Divide per Day":
        days = endDate.diff(startDate, "days");
        for (let i = 0; i <= days; i += 1) {
          const newFormData = { ...formData };
          newFormData.name = `${newFormData.name} ${i + 1}/${days + 1}`;
          newFormData.start_date = startDate
            .add(i, "day")
            .format("YYYY-MM-DDTHH:mm:ssZ")
            .replace(/[-+]\d\d:\d\d$/, "");
          newFormData.end_date = endDate
            .subtract(days - i, "day")
            .format("YYYY-MM-DDTHH:mm:ssZ")
            .replace(/[-+]\d\d:\d\d$/, "");
          dispatch(submitShift(newFormData)).then((response) => {
            if (response.status === "success") {
              dispatch(showNotification("Shift saved"));
              const new_shift_id = response?.data?.id;
              if (new_shift_id) {
                dispatch(fetchShift(new_shift_id));
              }
            }
          });
        }
        break;
      case "Divide per Week":
        days = endDate.diff(startDate, "days");
        weeks = Math.ceil(days / 7);
        for (let i = 0; i < weeks; i += 1) {
          const newFormData = { ...formData };
          newFormData.name = `${newFormData.name} ${i + 1}/${weeks}`;
          newFormData.start_date = startDate
            .add(i * 7, "day")
            .format("YYYY-MM-DDTHH:mm:ssZ")
            .replace(/[-+]\d\d:\d\d$/, "");
          if (i === weeks - 1) {
            newFormData.end_date = endDate
              .format("YYYY-MM-DDTHH:mm:ssZ")
              .replace(/[-+]\d\d:\d\d$/, "");
          } else {
            newFormData.end_date = startDate
              .add((i + 1) * 7, "day")
              .format("YYYY-MM-DDTHH:mm:ssZ")
              .replace(/[-+]\d\d:\d\d$/, "");
          }
          dispatch(submitShift(newFormData)).then((response) => {
            if (response.status === "success") {
              dispatch(showNotification("Shift saved"));
              const new_shift_id = response?.data?.id;
              if (new_shift_id) {
                dispatch(fetchShift(new_shift_id));
              }
            }
          });
        }
        break;
      default:
        break;
    }
  };

  function validate(formData, errors) {
    if (isDailyShift(formData.name)) {
      errors.name.addError(
        'Shift name cannot contain "number/number" at the end of the name, please fix.',
      );
    }
    if (formData.localTime === "local") {
      if (nowDate > formData.end_date_local) {
        errors.end_date_local.addError(
          "End date must be after current date, please fix.",
        );
      }
      if (formData.start_date_local > formData.end_date_local) {
        errors.start_date_local.addError(
          "Start date must be before end date, please fix.",
        );
      }
    } else if (formData.localTime === "UTC") {
      if (nowDateUTC > formData.end_date_utc) {
        errors.end_date_utc.addError(
          "End date must be after current date, please fix.",
        );
      }
      if (formData.start_date_utc > formData.end_date_utc) {
        errors.start_date_utc.addError(
          "Start date must be before end date, please fix.",
        );
      }
    }
    return errors;
  }

  const uiSchema = {
    divide: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
  };

  const shiftFormSchema = {
    type: "object",
    properties: {
      group_id: {
        type: "integer",
        oneOf: (groups || []).map((group) => ({
          enum: [group.id],
          type: "integer",
          title: `${group.name}`,
        })),
        title: "Group",
        default: groups ? groups[0]?.id : null,
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
      divide: {
        type: "string",
        title:
          "Do you want to divide the selected period in multiple shifts, daily or weekly?",
        enum: [
          "Divide per Week",
          "Divide per Day",
          "Don't divide, just create one shift",
        ],
        default: "Don't divide, just create one shift",
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

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { submitShift } from "../../ducks/shifts";
import { userLabel } from "../../utils/format";
import PropTypes from "prop-types";

dayjs.extend(utc);

const format = (date) => date.format("YYYY-MM-DDTHH:mm:ss");
const fromUtcToLocal = (date) => format(dayjs(`${date}Z`).local());
const fromLocalToUtc = (date) => format(dayjs(date).utc());

const NewShift = ({ preSelectedRange, setPreSelectedRange }) => {
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const groups = useSelector((state) => state.groups.userAccessible);
  const now = dayjs();
  const { users } = useSelector((state) => state.users);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [formData, setFormData] = useState({
    shift_admins: [currentUser.id],
    localTime: "local",
    start_date: format(now),
    end_date: format(now.add(1, "day")),
    divider: 6,
  });

  useEffect(() => {
    if (preSelectedRange) {
      setFormData((prevData) => ({
        ...prevData,
        ...(prevData.localTime === "local"
          ? {
              start_date: format(dayjs(preSelectedRange.start_date)),
              end_date: format(dayjs(preSelectedRange.end_date)),
            }
          : {
              start_date: fromUtcToLocal(preSelectedRange.start_date),
              end_date: fromUtcToLocal(preSelectedRange.end_date),
            }),
      }));
    }
  }, [preSelectedRange]);

  useEffect(() => {
    setAvailableUsers(
      users.filter(
        (user) =>
          user.id === currentUser.id ||
          (user.groups?.some((g) => g.id === formData.group_id) &&
            !user.is_bot),
      ),
    );
    formData.shift_admins = [currentUser.id];
  }, [users, formData.group_id, currentUser.id]);

  if (!groups || groups?.length === 0) {
    return <CircularProgress />;
  }

  const handleSubmit = async () => {
    const dataToSubmit = {
      group_id: formData.group_id,
      shift_admins: formData.shift_admins,
      name: formData.name,
      required_users_number: formData.required_users_number,
      description: formData.description,
      start_date: formData.start_date,
      end_date: formData.end_date,
    };

    // Convert dates to UTC format
    if (formData.localTime === "local") {
      dataToSubmit.start_date = fromLocalToUtc(dataToSubmit.start_date);
      dataToSubmit.end_date = fromLocalToUtc(dataToSubmit.end_date);
    }

    const startDate = dayjs(dataToSubmit.start_date);
    const endDate = dayjs(dataToSubmit.end_date);
    const shifts = [];

    switch (formData.divide) {
      case "Divide per Day": {
        const days = endDate.diff(startDate, "day");
        for (let i = 0; i <= days; i++) {
          shifts.push({
            ...dataToSubmit,
            name: `${dataToSubmit.name} ${i + 1}/${days + 1}`,
            start_date: format(startDate.add(i, "day")),
            end_date: format(startDate.add(i + 1, "day")),
          });
        }
        break;
      }

      case "Divide per Week": {
        const totalDays = endDate.diff(startDate, "day");
        const weeks = Math.ceil(totalDays / 7);
        for (let i = 0; i < weeks; i++) {
          const start = startDate.add(i * 7, "day");
          const end =
            i === weeks - 1 ? endDate : startDate.add((i + 1) * 7, "day");
          shifts.push({
            ...dataToSubmit,
            name: `${dataToSubmit.name} ${i + 1}/${weeks}`,
            start_date: format(start),
            end_date: format(end),
          });
        }
        break;
      }

      case "Divide per Hour": {
        const hourCount = Number(formData.divider);
        if (!hourCount || hourCount <= 0) {
          dispatch(
            showNotification(
              "Please provide a valid number of hours per shift.",
            ),
          );
          return;
        }
        const totalHours = endDate.diff(startDate, "hour");
        const segments = Math.ceil(totalHours / hourCount);
        for (let i = 0; i < segments; i++) {
          const start = startDate.add(i * hourCount, "hour");
          const end =
            i === segments - 1
              ? endDate
              : startDate.add((i + 1) * hourCount, "hour");
          shifts.push({
            ...dataToSubmit,
            name: `${dataToSubmit.name} ${i + 1}/${segments}`,
            start_date: format(start),
            end_date: format(end),
          });
        }
        break;
      }

      default:
        shifts.push(dataToSubmit);
        break;
    }

    // Dispatch all shifts
    for (const shift of shifts) {
      const response = await dispatch(submitShift(shift));
      if (response.status === "success") {
        dispatch(showNotification("Shift created successfully"));
      }
    }
    setPreSelectedRange(null);
  };

  function validate(_, errors) {
    if (/\d+\/\d+$/.test(formData.name)) {
      errors.name.addError(
        'Shift name cannot contain "number/number" at the end of the name, please fix.',
      );
    }
    if (formData.localTime === "local") {
      if (format(now) > formData.end_date) {
        errors.end_date.addError(
          "End date must be after current date, please fix.",
        );
      }
      if (formData.start_date > formData.end_date) {
        errors.start_date.addError(
          "Start date must be before end date, please fix.",
        );
      }
    } else if (formData.localTime === "UTC") {
      if (format(now.utc()) > formData.end_date) {
        errors.end_date.addError(
          "End date must be after current date, please fix.",
        );
      }
      if (formData.start_date > formData.end_date) {
        errors.start_date.addError(
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
      shift_admins: {
        type: "array",
        title: "Shift admins",
        items: {
          oneOf:
            availableUsers.length === 0
              ? [{ const: null, title: "No users available" }]
              : availableUsers.map((user) => ({
                  const: user.id,
                  title: userLabel(user, true, true),
                })),
        },
        default: [currentUser.id],
        uniqueItems: true,
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
      localTime: {
        type: "string",
        oneOf: [
          { enum: ["local"], title: "Local Time" },
          { enum: ["UTC"], title: "UTC Time" },
        ],
        default: "local",
        title: "Use local or UTC time?",
      },
      divide: {
        type: "string",
        title:
          "Do you want to divide the selected period in multiple shifts, daily or weekly?",
        enum: [
          "Don't divide, just create one shift",
          "Divide per Week",
          "Divide per Day",
          "Divide per Hour",
        ],
      },
    },
    required: ["group_id", "name"],
    dependencies: {
      divide: {
        oneOf: [
          {
            properties: {
              divide: {
                enum: ["Divide per Hour"],
              },
              divider: {
                type: "integer",
                title: "How many hours per shift?",
                default: 6,
              },
            },
            required: ["divider"],
          },
        ],
      },
      localTime: {
        oneOf: [
          {
            properties: {
              localTime: {
                enum: ["local"],
              },
              start_date: {
                type: "string",
                title: "Start Date (Local Time)",
              },
              end_date: {
                type: "string",
                title: "End Date (Local Time)",
              },
            },
          },
          {
            properties: {
              localTime: {
                enum: ["UTC"],
              },
              start_date: {
                type: "string",
                title: "Start Date (UTC Time)",
              },
              end_date: {
                type: "string",
                title: "End Date (UTC Time)",
              },
            },
          },
        ],
      },
    },
  };

  const handleChange = (e) => {
    // Manage time conversion
    const { start_date, end_date, localTime } = e.formData;
    if (formData.localTime === "local" && localTime === "UTC") {
      e.formData.start_date = fromLocalToUtc(start_date);
      e.formData.end_date = fromLocalToUtc(end_date);
    } else if (formData.localTime === "UTC" && localTime === "local") {
      e.formData.start_date = fromUtcToLocal(start_date);
      e.formData.end_date = fromUtcToLocal(end_date);
    }
    setFormData(e.formData);
  };

  return (
    <div style={{ width: "100%" }}>
      <Form
        schema={shiftFormSchema}
        validator={validator}
        uiSchema={uiSchema}
        formData={formData}
        onChange={handleChange}
        onSubmit={handleSubmit}
        customValidate={validate}
      />
    </div>
  );
};

NewShift.propTypes = {
  preSelectedRange: PropTypes.shape({
    start_date: PropTypes.string,
    end_date: PropTypes.string,
  }),
  setPreSelectedRange: PropTypes.func,
};

export default NewShift;

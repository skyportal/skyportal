import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { showNotification } from "baselayer/components/Notifications";
import { submitShift } from "../ducks/shift";
import { fetchShifts } from "../ducks/shifts";

const NewShift = () => {
  const groups = useSelector((state) => state.groups.userAccessible);

  const dispatch = useDispatch();

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
        title: "Start Date",
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date UTC",
      },
    },
    required: ["group_id", "start_date", "end_date"],
  };

  return <Form schema={shiftFormSchema} onSubmit={handleSubmit} />;
};

export default NewShift;

import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import { submitObservingRun } from "../ducks/observingRun";

const NewObservingRun = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();

  const handleSubmit = ({ formData }) => {
    dispatch(submitObservingRun(formData));
  };

  const observingRunFormSchema = {
    type: "object",
    properties: {
      pi: {
        type: "string",
        title: "PI",
      },
      calendar_date: {
        type: "string",
        format: "date",
        title: "Calendar Date",
      },
      observers: {
        type: "string",
        title: "Observers",
      },
      instrument_id: {
        type: "integer",
        oneOf: instrumentList.map((instrument) => ({
          enum: [instrument.id],
          title: `${
            telescopeList.find(
              (telescope) => telescope.id === instrument.telescope_id
            )?.name
          } / ${instrument.name}`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
      group_id: {
        type: "integer",
        oneOf: [{ enum: [null], title: "No group" }].concat(
          groups.map((group) => ({ enum: [group.id], title: group.name }))
        ),
        default: { enum: [null], title: "No group" },
        title: "Group",
      },
    },
    required: ["pi", "calendar_date", "instrument_id"],
  };

  return <Form schema={observingRunFormSchema} onSubmit={handleSubmit} />;
};

export default NewObservingRun;

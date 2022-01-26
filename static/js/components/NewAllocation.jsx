import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import { showNotification } from "baselayer/components/Notifications";
import { submitAllocation } from "../ducks/allocation";
import { fetchAllocations } from "../ducks/allocations";

const NewAllocation = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitAllocation(formData));
    if (result.status === "success") {
      dispatch(showNotification("Allocation saved"));
      dispatch(fetchAllocations());
    }
  };

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    return errors;
  }

  const allocationFormSchema = {
    type: "object",
    properties: {
      pi: {
        type: "string",
        title: "PI",
      },
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date",
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date",
      },
      hours_allocated: {
        type: "number",
        title: "Hours allocated",
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
        oneOf: groups.map((group) => ({
          enum: [group.id],
          title: `${group.name}`,
        })),
        title: "Group",
        default: groups[0]?.id,
      },
      _altdata: {
        type: "string",
        title: "Alternative json data (i.e. {'slack_token': 'testtoken'}",
      },
    },
    required: [
      "pi",
      "start_date",
      "end_date",
      "instrument_id",
      "hours_allocated",
    ],
  };

  return (
    <Form
      schema={allocationFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
    />
  );
};

export default NewAllocation;

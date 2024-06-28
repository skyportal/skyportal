import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { submitObservingRun } from "../../ducks/observingRun";

dayjs.extend(utc);

const NewObservingRun = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();

  const defaultDate = dayjs().utc().format("YYYY-MM-DD");

  const handleSubmit = async ({ formData }) => {
    if (formData.group_id === -1) {
      delete formData.group_id;
    }
    const result = await dispatch(submitObservingRun(formData));
    if (result.status === "success") {
      dispatch(showNotification("Observing run saved"));
    }
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
        default: defaultDate,
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
              (telescope) => telescope.id === instrument.telescope_id,
            )?.name
          } / ${instrument.name}`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
      group_id: {
        type: "integer",
        oneOf: [{ enum: [-1], title: "No group" }].concat(
          groups.map((group) => ({ enum: [group.id], title: group.name })),
        ),
        default: -1,
        title: "Group",
      },
    },
    required: ["pi", "calendar_date", "instrument_id"],
  };

  return (
    <Form
      schema={observingRunFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
    />
  );
};

export default NewObservingRun;

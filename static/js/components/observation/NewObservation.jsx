import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import {
  fetchObservations,
  uploadObservations,
} from "../../ducks/observations";

const NewObservation = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const ascii = dataUriToBuffer(formData.file).toString();
    const payload = {
      observationData: ascii,
      instrumentID: formData.instrument_id,
    };
    const result = await dispatch(uploadObservations(payload));
    if (result.status === "success") {
      dispatch(showNotification("Observation saved"));
      dispatch(fetchObservations());
    }
  };

  const observationFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Observation file",
        description: "Observation file",
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
    },
    required: ["file", "instrument_id"],
  };

  return (
    <Form
      schema={observationFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
    />
  );
};

export default NewObservation;

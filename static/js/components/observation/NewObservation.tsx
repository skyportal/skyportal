import React from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import {
  fetchObservations,
  uploadObservations,
} from "../../ducks/observations";

interface NewObservationProps {
  onClose?: (() => void) | null;
}

const NewObservation = ({ onClose = null }: NewObservationProps) => {
  const { instrumentList } = useAppSelector((state) => state.instruments);
  const { telescopeList } = useAppSelector((state) => state.telescopes);
  const dispatch = useAppDispatch();

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const parsed = dataUriToBuffer(formData.file);
    const ascii = new TextDecoder().decode(parsed.buffer);
    const payload = {
      observationData: ascii,
      instrumentID: formData.instrument_id,
    };
    const result: any = await dispatch(uploadObservations(payload));
    if (result.status === "success") {
      dispatch(showNotification("Observation saved"));
      dispatch(fetchObservations());
      if (typeof onClose === "function") {
        onClose();
      }
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
      schema={observationFormSchema as any}
      validator={validator}
      onSubmit={handleSubmit as any}
    />
  );
};

export default NewObservation;

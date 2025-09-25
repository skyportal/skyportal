import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";
import { fetchMMADetectors, submitMMADetector } from "../../ducks/mmadetector";

const NewMMADetector = () => {
  const { mmadetectorList } = useSelector((state) => state.mmadetectors);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitMMADetector(formData));
    if (result.status === "success") {
      dispatch(showNotification("MMADetector saved"));
      dispatch(fetchMMADetectors());
    }
  };

  const uiSchema = {
    fixed_location: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
  };

  function validate(formData, errors) {
    mmadetectorList?.forEach((mmadetector) => {
      if (formData.name === mmadetector.name) {
        errors.name.addError(
          "MMADetector name matches another, please change.",
        );
      }
    });
    if (formData.lon < -180 || formData.lon > 180) {
      errors.lon.addError("Longitude must be between -180 and 180.");
    }
    if (formData.lat < -90 || formData.lat > 90) {
      errors.lat.addError("Latitude must be between -90 and 90.");
    }

    return errors;
  }

  const mmadetectorFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
      },
      nickname: {
        type: "string",
        title: "Nickname (e.g., P200)",
      },
      type: {
        type: "string",
        oneOf: [
          { enum: ["gravitational-wave"], title: "Gravitational Wave" },
          { enum: ["neutrino"], title: "Neutrino" },
          { enum: ["gamma-ray-burst"], title: "Gamma-ray Burst" },
        ],
        title: "Type",
      },
      lat: {
        type: "number",
        title: "Latitude [deg]",
      },
      lon: {
        type: "number",
        title: "Longitude [deg]",
      },
      fixed_location: {
        type: "boolean",
        title: "Does this telescope have a fixed location (lon, lat)?",
      },
    },
    required: ["name", "nickname", "type", "fixed_location"],
  };

  return (
    <Form
      schema={mmadetectorFormSchema}
      validator={validator}
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
      customValidate={validate}
    />
  );
};

export default NewMMADetector;

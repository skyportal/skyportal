import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import { showNotification } from "baselayer/components/Notifications";
import { submitGWDetector, fetchGWDetectors } from "../ducks/gwdetector";

const NewGWDetector = () => {
  const { gwdetectorList } = useSelector((state) => state.gwdetectors);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitGWDetector(formData));
    if (result.status === "success") {
      dispatch(showNotification("GWDetector saved"));
      dispatch(fetchGWDetectors());
    }
  };

  function validate(formData, errors) {
    gwdetectorList?.forEach((gwdetector) => {
      if (formData.name === gwdetector.name) {
        errors.name.addError("GWDetector name matches another, please change.");
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

  const gwdetectorFormSchema = {
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
      lat: {
        type: "number",
        title: "Latitude [deg]",
      },
      lon: {
        type: "number",
        title: "Longitude [deg]",
      },
    },
    required: ["name", "nickname", "lat", "lon"],
  };

  return (
    <Form
      schema={gwdetectorFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
    />
  );
};

export default NewGWDetector;

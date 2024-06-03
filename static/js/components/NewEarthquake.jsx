import React from "react";
import { useDispatch } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { fetchEarthquakes, submitEarthquake } from "../ducks/earthquake";

dayjs.extend(utc);

const NewEarthquake = () => {
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitEarthquake(formData));
    if (result.status === "success") {
      dispatch(showNotification("Earthquake saved"));
      dispatch(fetchEarthquakes());
    }
  };

  const defaultDate = dayjs()
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ")
    .replace("+00:00", "");

  function validate(formData, errors) {
    if (formData.lon < -180 || formData.lon > 180) {
      errors.lon.addError("Longitude must be between -180 and 180.");
    }
    if (formData.lat < -90 || formData.lat > 90) {
      errors.lat.addError("Latitude must be between -90 and 90.");
    }

    return errors;
  }

  const earthquakeFormSchema = {
    type: "object",
    properties: {
      event_id: {
        type: "string",
        title: "Name",
      },
      date: {
        type: "string",
        title: "Date (UTC)",
        default: defaultDate,
      },
      latitude: {
        type: "number",
        title: "Latitude [deg]",
      },
      longitude: {
        type: "number",
        title: "Longitude [deg]",
      },
      depth: {
        type: "number",
        title: "Depth [m]",
      },
      magnitude: {
        type: "number",
        title: "Magnitude",
      },
    },
    required: [
      "event_id",
      "date",
      "latitude",
      "longitude",
      "depth",
      "magnitude",
    ],
  };

  return (
    <Form
      schema={earthquakeFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      customValidate={validate}
    />
  );
};

export default NewEarthquake;

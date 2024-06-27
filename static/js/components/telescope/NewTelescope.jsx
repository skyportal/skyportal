import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";
import { submitTelescope } from "../../ducks/telescope";
import { fetchTelescopes } from "../../ducks/telescopes";

const NewTelescope = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitTelescope(formData));
    if (result.status === "success") {
      dispatch(showNotification("Telescope saved"));
      dispatch(fetchTelescopes());
    }
  };

  const uiSchema = {
    robotic: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
    fixed_location: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
  };

  function validate(formData, errors) {
    telescopeList?.forEach((telescope) => {
      if (formData.name === telescope.name) {
        errors.name.addError("Telescope name matches another, please change.");
      }
    });
    if (formData.fixed_location === true) {
      if (formData.lon === undefined) {
        errors.lon.addError(
          "Longitude must be specified if telescope is fixed.",
        );
      } else if (formData.lon < -180 || formData.lon > 180) {
        errors.lon.addError("Longitude must be between -180 and 180.");
      }
      if (formData.lat === undefined) {
        errors.lat.addError(
          "Latitude must be specified if telescope is fixed.",
        );
      } else if (formData.lat < -90 || formData.lat > 90) {
        errors.lat.addError("Latitude must be between -90 and 90.");
      }
      if (formData.elevation === undefined) {
        errors.elevation.addError(
          "Elevation must be specified if telescope is fixed.",
        );
      } else if (formData.elevation < 0) {
        errors.elevation.addError("Elevation must be positive.");
      }
    }

    return errors;
  }

  const telescopeFormSchema = {
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
      elevation: {
        type: "number",
        title: "Elevation [m]",
      },
      diameter: {
        type: "number",
        title: "Diameter [m]",
      },
      skycam_link: {
        type: "string",
        title: "Sky camera URL",
      },
      weather_link: {
        type: "string",
        title: "Preferred weather site URL",
      },
      robotic: {
        type: "boolean",
        title: "Is this telescope robotic?",
      },
      fixed_location: {
        type: "boolean",
        title: "Does this telescope have a fixed location (lon, lat, elev)?",
      },
    },
    required: ["name", "nickname", "diameter", "robotic", "fixed_location"],
  };

  return (
    <Form
      schema={telescopeFormSchema}
      validator={validator}
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      customValidate={validate}
    />
  );
};

export default NewTelescope;

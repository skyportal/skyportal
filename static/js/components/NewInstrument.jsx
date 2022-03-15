import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { submitInstrument } from "../ducks/instrument";
import { fetchInstruments } from "../ducks/instruments";

const NewInstrument = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    if (Object.keys(formData).includes("api_classname")) {
      // eslint-disable-next-line prefer-destructuring
      formData.api_classname = formData.api_classname[0];
    }
    if (Object.keys(formData).includes("api_classname_obsplan")) {
      // eslint-disable-next-line prefer-destructuring
      formData.api_classname_obsplan = formData.api_classname_obsplan[0];
    }
    if (Object.keys(formData).includes("field_data")) {
      formData.field_data = dataUriToBuffer(formData.field_data).toString();
    }
    if (Object.keys(formData).includes("field_region")) {
      formData.field_region = dataUriToBuffer(formData.field_region).toString();
    }
    if (Object.keys(formData).includes("field_fov_type")) {
      // eslint-disable-next-line prefer-destructuring
      formData.field_fov_type = formData.field_fov_type[0];
    }
    if (Object.keys(formData).includes("field_fov_attributes")) {
      // eslint-disable-next-line prefer-destructuring
      formData.field_fov_attributes = formData.field_fov_attributes.split(",");
    }
    const result = await dispatch(submitInstrument(formData));
    if (result.status === "success") {
      dispatch(showNotification("Instrument saved"));
      dispatch(fetchInstruments());
    }
  };

  if (enum_types.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const api_classnames = [...enum_types.ALLOWED_API_CLASSNAMES].sort();
  api_classnames.push("");
  const filters = [...enum_types.ALLOWED_BANDPASSES].sort();

  function validate(formData, errors) {
    instrumentList?.forEach((instrument) => {
      if (formData.name === instrument.name) {
        errors.name.addError("Instrument name matches another, please change.");
      }
    });
    if (errors && formData.api_classname && formData.api_classname.length > 1) {
      errors.api_classname.addError("Must only choose one API class.");
    }
    if (
      errors &&
      formData.api_classname_obsplan &&
      formData.api_classname_obsplan.length > 1
    ) {
      errors.api_classname_obsplan.addError("Must only choose one API class.");
    }
    if (
      errors &&
      formData.field_fov_type &&
      formData.field_fov_type.length > 1
    ) {
      errors.field_fov_type.addError("Must only choose one FOV type.");
    }
    if (errors && formData.field_region && formData.field_fov_type) {
      errors.field_region.addError(
        "Must only choose either field_region or field_fov_type."
      );
    }
    if (errors && formData.field_fov_type && formData.field_fov_attributes) {
      if (formData.field_fov_type[0] === "circle") {
        if (formData.field_fov_attributes.split(",").length !== 1) {
          errors.field_fov_attributes.addError(
            "For the circle option, field_fov_attributes should be a single number (radius in degrees)."
          );
        }
      } else if (formData.field_fov_type[0] === "rectangle") {
        if (formData.field_fov_attributes.split(",").length !== 2) {
          errors.field_fov_attributes.addError(
            "For the rectangle option, field_fov_attributes should be two numbers (width and height in degrees)."
          );
        }
      }
    }
    return errors;
  }

  const instrumentFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
      },
      type: {
        type: "string",
        oneOf: [
          { enum: ["imager"], title: "Imager" },
          { enum: ["imaging spectrograph"], title: "Imaging Spectrograph" },
          { enum: ["spectrograph"], title: "Spectrograph" },
        ],
        title: "Type",
      },
      band: {
        type: "string",
        title: "Band (e.g., Optical, IR)",
      },
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
      },
      telescope_id: {
        type: "integer",
        oneOf: telescopeList.map((telescope) => ({
          enum: [telescope.id],
          title: `${telescope.name}`,
        })),
        title: "Telescope",
        default: telescopeList[0]?.id,
      },
      api_classname: {
        type: "array",
        items: {
          type: "string",
          enum: api_classnames,
        },
        uniqueItems: true,
        title: "API Classname",
      },
      api_classname_obsplan: {
        type: "array",
        items: {
          type: "string",
          enum: api_classnames,
        },
        uniqueItems: true,
        title: "API Observation Plan Classname",
      },
      field_data: {
        type: "string",
        format: "data-url",
        title: "Field data file",
        description: "Field data file",
      },
      field_region: {
        type: "string",
        format: "data-url",
        title: "Field region file",
        description: "Field region file",
      },
      field_fov_type: {
        type: "array",
        items: {
          type: "string",
          enum: ["rectangle", "circle"],
        },
        uniqueItems: true,
        title: "FOV Type",
        description: "Rectangle or Circle",
      },
      field_fov_attributes: {
        type: "string",
        title: "FOV Attributes",
        description: "Rectangle [width,height]; Circle [radius]",
      },
    },
    required: ["name", "type", "band", "telescope_id"],
  };

  return (
    <Form
      schema={instrumentFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
      liveValidate
    />
  );
};

export default NewInstrument;

import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as sourceActions from "../ducks/source";

dayjs.extend(utc);

const ImageAnalysisForm = ({ obj_id }) => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const defaultDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = async ({ formData }) => {
    formData.obstime = formData.obstime
      .replace("+00:00", "")
      .replace(".000Z", "");

    if (Object.keys(formData).includes("image_file")) {
      formData.image_data = dataUriToBuffer(formData.image_file).toString();
    }
    const result = await dispatch(
      sourceActions.submitImageAnalysis(obj_id, formData)
    );
    if (result.status === "success") {
      dispatch(showNotification("Image analysis complete"));
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

  const imageAnalysisFormSchema = {
    type: "object",
    properties: {
      obstime: {
        type: "string",
        format: "date-time",
        title: "Image Date [UTC]",
        default: defaultDate,
      },
      filter: {
        type: "string",
        oneOf: filters.map((filter) => ({
          enum: [filter],
          title: `${filter}`,
        })),
        title: "Filter list",
        default: filters[0],
      },
      instrument_id: {
        type: "integer",
        oneOf: instrumentList.map((instrument) => ({
          enum: [instrument.id],
          title: `${instrument.name}`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
      image_file: {
        type: "string",
        format: "data-url",
        title: "Image data file",
        description: "Image data file",
      },
    },
    required: ["obstime", "filter", "image_file", "instrument_id"],
  };

  return (
    <Form
      schema={imageAnalysisFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
      liveValidate
    />
  );
};

ImageAnalysisForm.propTypes = {
  obj_id: PropTypes.number.isRequired,
};

export default ImageAnalysisForm;

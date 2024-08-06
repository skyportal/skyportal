import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { modifyInstrument } from "../../ducks/instrument";
import { fetchInstruments } from "../../ducks/instruments";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  allocationSelect: {
    width: "100%",
  },
  localizationSelect: {
    width: "100%",
  },
  allocationSelectItem: {
    whiteSpace: "break-spaces",
  },
  localizationSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

const ModifyInstrument = ({ instrumentID, onClose }) => {
  const classes = useStyles();
  const textClasses = textStyles();

  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    if (
      Object.keys(formData).includes("api_classname") &&
      formData.api_classname !== undefined
    ) {
      formData.api_classname = formData.api_classname[0];
    }
    if (
      Object.keys(formData).includes("api_classname_obsplan") &&
      formData.api_classname_obsplan !== undefined
    ) {
      formData.api_classname_obsplan = formData.api_classname_obsplan[0];
    }
    if (
      Object.keys(formData).includes("field_data") &&
      formData.field_data !== undefined
    ) {
      const parsed_field_data = dataUriToBuffer(formData.field_data);
      formData.field_data = new TextDecoder().decode(parsed_field_data.buffer);
    }
    if (
      Object.keys(formData).includes("field_region") &&
      formData.field_region !== undefined
    ) {
      const parsed_field_region = dataUriToBuffer(formData.field_region);
      formData.field_region = new TextDecoder().decode(
        parsed_field_region.buffer,
      );
    }
    if (
      Object.keys(formData).includes("references") &&
      formData.references !== undefined
    ) {
      const parsed_references = dataUriToBuffer(formData.references);
      formData.references = new TextDecoder().decode(parsed_references.buffer);
    }
    if (
      Object.keys(formData).includes("field_fov_type") &&
      formData.field_fov_type !== undefined
    ) {
      formData.field_fov_type = formData.field_fov_type[0];
    }
    if (
      Object.keys(formData).includes("field_fov_attributes") &&
      formData.field_fov_attributes !== undefined
    ) {
      formData.field_fov_attributes = formData.field_fov_attributes.split(",");
    }
    const result = await dispatch(modifyInstrument(instrumentID, formData));
    if (result.status === "success") {
      dispatch(showNotification("Instrument saved"));
      dispatch(fetchInstruments());
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  if (instrumentList.length === 0 || telescopeList.length === 0) {
    return <h3>No instruments available...</h3>;
  }

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

  if (telescopeList.length === 0 || instrumentList.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const telLookUp = {};

  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp = {};

  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const oldFilters = [];
  instLookUp[instrumentID]?.filters?.forEach((filter) => {
    oldFilters.push(filter);
  });

  function validate(formData, errors) {
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
    if (errors && formData.field_region && formData.field_fov_type.length > 0) {
      errors.field_region.addError(
        "Must only choose either field_region or field_fov_type.",
      );
    }
    if (errors && formData.field_fov_type && formData.field_fov_attributes) {
      if (formData.field_fov_type[0] === "circle") {
        if (formData.field_fov_attributes.split(",").length !== 1) {
          errors.field_fov_attributes.addError(
            "For the circle option, field_fov_attributes should be a single number (radius in degrees).",
          );
        }
      } else if (formData.field_fov_type[0] === "rectangle") {
        if (formData.field_fov_attributes.split(",").length !== 2) {
          errors.field_fov_attributes.addError(
            "For the rectangle option, field_fov_attributes should be two numbers (width and height in degrees).",
          );
        }
      }
    }
    return errors;
  }

  const instrumentFormSchema = {
    type: "object",
    properties: {
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
        default: oldFilters,
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
      references: {
        type: "string",
        format: "data-url",
        title: "References file",
        description: "References file",
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
      sensitivity_data: {
        type: "string",
        title:
          "Sensitivity data i.e. {'ztfg': {'limiting_magnitude': 20.3, 'magsys': 'ab', 'exposure_time': 30, 'zeropoint': 26.3,}}",
      },
      configuration_data: {
        type: "string",
        title:
          "Configuration data i.e. {'overhead_per_exposure': 2.0, 'readout': 8.0, 'slew_rate': 2.6, 'filt_change_time': 60.0}",
      },
    },
  };

  return (
    <div className={classes.container}>
      <Form
        schema={instrumentFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        customValidate={validate}
        liveValidate
      />
    </div>
  );
};

ModifyInstrument.propTypes = {
  instrumentID: PropTypes.number.isRequired,
  onClose: PropTypes.func,
};

ModifyInstrument.defaultProps = {
  onClose: null,
};

export default ModifyInstrument;

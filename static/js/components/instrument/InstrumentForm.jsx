import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { submitInstrument } from "../../ducks/instrument";
import { modifyInstrument } from "../../ducks/instrument";
import { fetchInstruments } from "../../ducks/instruments";

const InstrumentForm = ({ onClose, instrumentID = null }) => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const keys = Object.keys(formData);
    if (keys.includes("field_data") && formData.field_data) {
      const parsed_field_data = dataUriToBuffer(formData.field_data);
      formData.field_data = new TextDecoder().decode(parsed_field_data.buffer);
    }
    if (keys.includes("field_region") && formData.field_region) {
      const parsed_field_region = dataUriToBuffer(formData.field_region);
      formData.field_region = new TextDecoder().decode(
        parsed_field_region.buffer,
      );
    }
    if (keys.includes("references") && formData.references) {
      const parsed_references = dataUriToBuffer(formData.references);
      formData.references = new TextDecoder().decode(parsed_references.buffer);
    }
    formData.field_fov_attributes = formData.field_fov_attributes?.split(",");

    const result = await dispatch(
      instrumentID
        ? modifyInstrument(instrumentID, formData)
        : submitInstrument(formData),
    );
    if (result.status === "success") {
      dispatch(showNotification("Instrument saved"));
      dispatch(fetchInstruments());
      onClose();
    }
  };

  if (instrumentList.length === 0 || telescopeList.length === 0) {
    return <h3>No instruments available...</h3>;
  } else if (enum_types.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const api_classnames = [...enum_types.ALLOWED_API_CLASSNAMES].sort();
  const filters = [...enum_types.ALLOWED_BANDPASSES].sort();

  const instrumentToEdit = instrumentID
    ? instrumentList.find((inst) => inst.id === instrumentID)
    : null;
  if (instrumentID && !instrumentToEdit) {
    return <h3>Instrument not found !</h3>;
  }

  function validate(formData, errors) {
    if (
      instrumentID === null &&
      instrumentList?.some((instrument) => formData.name === instrument.name)
    ) {
      errors.name.addError("Instrument name matches another, please change.");
    }
    if (formData.field_region && formData.field_fov_type) {
      errors.field_region.addError(
        "Must only choose either field_region or field_fov_type.",
      );
    }
    if (formData.field_fov_type && formData.field_fov_attributes) {
      const attributes = formData.field_fov_attributes.split(",");
      if (formData.field_fov_type === "circle" && attributes.length !== 1) {
        errors.field_fov_attributes.addError(
          "For the circle option, field_fov_attributes should be a single number (radius in degrees).",
        );
      } else if (
        formData.field_fov_type === "rectangle" &&
        attributes.length !== 2
      ) {
        errors.field_fov_attributes.addError(
          "For the rectangle option, field_fov_attributes should be two numbers (width and height in degrees).",
        );
      }
    }
    return errors;
  }

  const instrumentFormSchema = {
    type: "object",
    properties: {
      ...(instrumentToEdit
        ? {}
        : {
            name: {
              type: "string",
              title: "Name",
            },
            telescope_id: {
              type: "integer",
              oneOf: telescopeList.map((telescope) => ({
                enum: [telescope.id],
                title: `${telescope.name}`,
              })),
              title: "Telescope",
            },
            treasuremap_id: {
              type: "integer",
              title: "Treasuremap ID",
              description:
                "ID of the instrument to submit to Treasuremap (optional)",
            },
            type: {
              type: "string",
              oneOf: [
                { enum: ["imager"], title: "Imager" },
                {
                  enum: ["imaging spectrograph"],
                  title: "Imaging Spectrograph",
                },
                { enum: ["spectrograph"], title: "Spectrograph" },
              ],
              title: "Type",
            },
            band: {
              type: "string",
              title: "Band (e.g., Optical, IR)",
            },
          }),
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
        default: instrumentToEdit?.filters || [],
      },
      api_classname: {
        type: "string",
        enum: api_classnames,
        uniqueItems: true,
        title: "API Classname",
        default: instrumentToEdit?.api_classname || undefined,
      },
      api_classname_obsplan: {
        type: "string",
        enum: api_classnames,
        uniqueItems: true,
        title: "API Observation Plan Classname",
        default: instrumentToEdit?.api_classname_obsplan || undefined,
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
        type: "string",
        oneOf: [
          {
            enum: ["rectangle"],
            title: "rectangle",
          },
          {
            enum: ["circle"],
            title: "circle",
          },
        ],
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
    ...(instrumentID
      ? {}
      : { required: ["name", "type", "band", "telescope_id"] }),
  };

  const uiSchema = {
    api_classname: {
      "ui:placeholder": "Choose an option",
    },
    api_classname_obsplan: {
      "ui:placeholder": "Choose an option",
    },
    field_fov_type: {
      "ui:placeholder": "Choose an option",
    },
  };

  return (
    <Form
      schema={instrumentFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
      customValidate={validate}
      liveValidate
      uiSchema={uiSchema}
    />
  );
};

InstrumentForm.propTypes = {
  onClose: PropTypes.func.isRequired,
  instrumentID: PropTypes.number,
};

InstrumentForm.defaultProps = {
  instrumentID: null,
};

export default InstrumentForm;

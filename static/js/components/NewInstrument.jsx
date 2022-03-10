import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { submitInstrument } from "../ducks/instrument";
import { fetchInstruments } from "../ducks/instruments";

const NewInstrument = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
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
    const result = await dispatch(submitInstrument(formData));
    if (result.status === "success") {
      dispatch(showNotification("Instrument saved"));
      dispatch(fetchInstruments());
    }
  };

  const api_classnames = [];
  instrumentList?.forEach((instrument) => {
    if (instrument.api_classname) {
      api_classnames.push(instrument.api_classname);
    }
    if (instrument.api_classname_obsplan) {
      api_classnames.push(instrument.api_classname_obsplan);
    }
  });
  api_classnames.push("");
  const api_classnames_unique = [...new Set(api_classnames)];

  const filters = [];
  instrumentList?.forEach((instrument) => {
    instrument.filters?.forEach((filter) => {
      filters.push(filter);
    });
  });
  const filtersUnique = [...new Set(filters)];

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
          enum: filtersUnique,
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
          enum: api_classnames_unique,
        },
        uniqueItems: true,
        title: "API Classname",
      },
      api_classname_obsplan: {
        type: "array",
        items: {
          type: "string",
          enum: api_classnames_unique,
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

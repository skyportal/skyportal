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
    if (formData.group_id === -1) {
      delete formData.group_id;
    }
    if (formData.field_data === -1) {
      delete formData.field_data;
    } else {
      formData.field_data = dataUriToBuffer(formData.field_data).toString();
    }
    if (formData.field_region === -1) {
      delete formData.field_region;
    } else {
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
      api_classnames.push({
        enum: [instrument.api_classname],
        title: instrument.api_classname,
      });
    }
  });
  api_classnames.push({ enum: [""], title: "No API" });

  const filters = [];
  instrumentList?.forEach((instrument) => {
    instrument.filters?.forEach((filter) => {
      filters.push(filter);
    });
  });
  const filtersUnique = [...new Set(filters)];

  const uiSchema = {
    filters: {
      "ui:widget": "checkboxes",
      "ui:column": "is-6",
    },
  };

  function validate(formData, errors) {
    instrumentList?.forEach((instrument) => {
      if (formData.name === instrument.name) {
        errors.name.addError("Instrument name matches another, please change.");
      }
    });
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
        type: "string",
        anyOf: api_classnames,
        title: "API Classname",
        default: api_classnames[0]?.enum,
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
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
    />
  );
};

export default NewInstrument;

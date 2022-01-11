import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import { showNotification } from "baselayer/components/Notifications";
import { submitInstrument } from "../ducks/instrument";

const NewInstrument = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    if (formData.group_id === -1) {
      delete formData.group_id;
    }
    const result = await dispatch(submitInstrument(formData));
    if (result.status === "success") {
      dispatch(showNotification("Instrument saved"));
    }
  };

  const api_classnames = [{ enum: [null], title: "No API" }];
  instrumentList?.forEach((instrument) => {
    if (instrument.api_classname) {
      api_classnames.push({
        enum: [instrument.api_classname],
        title: instrument.api_classname,
      });
    }
  });

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
    },
  };

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
        oneOf: api_classnames,
        title: "API Classname",
      },
    },
    required: ["name", "type", "band", "telescope_id"],
  };

  return (
    <Form
      schema={instrumentFormSchema}
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
    />
  );
};

export default NewInstrument;

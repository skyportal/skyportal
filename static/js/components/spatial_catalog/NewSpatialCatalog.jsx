import React from "react";
import { useDispatch } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import {
  fetchSpatialCatalogs,
  uploadSpatialCatalogs,
} from "../../ducks/spatialCatalogs";

const NewSpatialCatalog = () => {
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const ascii = dataUriToBuffer(formData.file).toString();
    const payload = {
      catalogData: ascii,
      catalogName: formData.catalogName,
    };
    const result = await dispatch(uploadSpatialCatalogs(payload));
    if (result.status === "success") {
      dispatch(
        showNotification("Saving spatial catalog... please be patient."),
      );
      dispatch(fetchSpatialCatalogs());
    }
  };

  const spatialCatalogFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Spatial catalog file",
        description: "Spatial catalog file",
      },
      catalogName: {
        type: "string",
        title: "Spatial catalog name",
        description: "Spatial catalog name",
      },
    },
    required: ["file", "catalogName"],
  };

  return (
    <Form
      schema={spatialCatalogFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
    />
  );
};

export default NewSpatialCatalog;

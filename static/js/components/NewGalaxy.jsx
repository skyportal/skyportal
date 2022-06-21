import React from "react";
import { useDispatch } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { fetchGalaxies, uploadGalaxies } from "../ducks/galaxies";

const NewGalaxy = () => {
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const ascii = dataUriToBuffer(formData.file).toString();
    const payload = {
      catalogData: ascii,
      catalogName: formData.catalogName,
    };
    const result = await dispatch(uploadGalaxies(payload));
    if (result.status === "success") {
      dispatch(showNotification("Galaxy saved"));
      dispatch(fetchGalaxies());
    }
  };

  const galaxyFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Galaxy catalog file",
        description: "Galaxy file",
      },
      catalogName: {
        type: "string",
        title: "Galaxy catalog name",
        description: "Galaxy catalog name",
      },
    },
    required: ["file", "catalogName"],
  };

  return <Form schema={galaxyFormSchema} onSubmit={handleSubmit} />;
};

export default NewGalaxy;

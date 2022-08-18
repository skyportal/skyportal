import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { submitGcnEvent } from "../ducks/gcnEvent";

import * as gcnTagsActions from "../ducks/gcnTags";

const NewGcnEvent = () => {
  const dispatch = useDispatch();

  let gcnTags = [];
  gcnTags = gcnTags.concat(useSelector((state) => state.gcnTags));
  gcnTags.sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  const handleSubmit = async ({ formData }) => {
    if (Object.keys(formData).includes("xml")) {
      // eslint-disable-next-line prefer-destructuring
      formData.xml = dataUriToBuffer(formData.xml).toString();
    }
    if (Object.keys(formData).includes("ra")) {
      // eslint-disable-next-line prefer-destructuring
      formData.skymap = {
        ra: formData.ra,
        dec: formData.dec,
        error: formData.error,
      };
    }
    const result = await dispatch(submitGcnEvent(formData));
    if (result.status === "success") {
      dispatch(showNotification("GCN Event saved"));
    }
  };

  function validate(formData, errors) {
    if (formData.ra < 0 || formData.ra >= 360) {
      errors.ra.addError("0 <= RA < 360, please fix.");
    }
    if (formData.dec < -90 || formData.dec > 90) {
      errors.dec.addError("-90 <= Declination <= 90, please fix.");
    }
    if (formData.error < 0) {
      errors.error.addError("0 < error, please fix.");
    }
    if (!formData.xml) {
      if (
        !formData.dateobs ||
        !formData.ra ||
        !formData.dec ||
        !formData.error
      ) {
        errors.dateobs.addError(
          "dateobs, ra, dec, and error must be defined if not uploading VOEvent"
        );
      }
    }
    return errors;
  }

  const gcnEventFormSchema = {
    type: "object",
    properties: {
      dateobs: {
        type: "string",
        title: "Observation date [i.e. 2022-05-14T12:24:25]",
      },
      ra: {
        type: "number",
        title: "Right Ascension [deg]",
      },
      dec: {
        type: "number",
        title: "Declination [deg]",
      },
      error: {
        type: "number",
        title: "1-sigma Error [deg]",
      },
      tags: {
        type: "array",
        items: {
          type: "string",
          enum: gcnTags,
        },
        uniqueItems: true,
        title: "Tags list",
      },
      xml: {
        type: "string",
        format: "data-url",
        title: "VOEvent XML File",
        description: "VOEvent XML file",
      },
    },
  };

  return (
    <Form
      schema={gcnEventFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
      liveValidate
    />
  );
};

export default NewGcnEvent;

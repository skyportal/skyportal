import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dataUriToBuffer from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";

import { submitGcnEvent } from "../../ducks/gcnEvent";
import * as gcnTagsActions from "../../ducks/gcnTags";

const NewGcnEvent = ({ handleClose = null }) => {
  const dispatch = useDispatch();

  let gcnTags = [];
  gcnTags = gcnTags.concat(useSelector((state) => state.gcnTags));
  gcnTags.sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  const handleSubmit = async ({ formData }) => {
    if (Object.keys(formData).includes("json") && formData.json !== undefined) {
      // eslint-disable-next-line prefer-destructuring
      formData.json = dataUriToBuffer(formData.json).toString();
    }
    if (Object.keys(formData).includes("xml") && formData.xml !== undefined) {
      // eslint-disable-next-line prefer-destructuring
      formData.xml = dataUriToBuffer(formData.xml).toString();
    }
    if (Object.keys(formData).includes("ra") && formData.ra !== undefined) {
      // eslint-disable-next-line prefer-destructuring
      formData.skymap = {
        ra: formData.ra,
        dec: formData.dec,
        error: formData.error,
      };
    }
    if (
      Object.keys(formData).includes("polygon") &&
      formData.polygon !== undefined
    ) {
      // eslint-disable-next-line prefer-destructuring
      formData.skymap = {
        localization_name: formData.localization_name,
        polygon: formData.polygon,
      };
    }
    const result = await dispatch(submitGcnEvent(formData));
    if (result.status === "success") {
      dispatch(showNotification("GCN Event saved"));
      if (handleClose) {
        handleClose();
      }
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
    if (!(formData.xml || formData.json)) {
      if (!formData.dateobs) {
        errors.dateobs.addError(
          "dateobs must be defined if not uploading a VOEvent or JSON notice",
        );
      }
      if (
        !formData.polygon &&
        !formData.skymap &&
        !(
          formData.ra !== undefined &&
          formData.dec !== undefined &&
          formData.error !== undefined
        )
      ) {
        errors.skymap.addError(
          "Either (i) ra, dec, and error or (ii) polygon or (iii) skymap must be defined if not uploading VOEvent / JSON",
        );
      }
      if (formData.polygon && !formData.localization_name) {
        errors.polygon.addError(
          "If polygon, must also specify localization name",
        );
      }
    }
    return errors;
  }

  const properties = {
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
    localization_name: {
      type: "string",
      title: "Localization name",
    },
    polygon: {
      type: "string",
      title:
        "Polygon [i.e. [(30.0, 60.0), (40.0, 60.0), (40.0, 70.0), (30.0, 70.0)] ]",
    },
    xml: {
      type: "string",
      format: "data-url",
      title: "VOEvent XML file",
      description: "VOEvent XML file",
    },
    json: {
      type: "string",
      format: "data-url",
      title: "JSON file",
      description: "JSON file",
    },
    skymap: {
      type: "string",
      format: "data-url",
      title: "Skymap File",
      description: "Skymap Fits file",
    },
  };

  if (gcnTags.length > 0) {
    properties.tags = {
      type: "array",
      items: {
        type: "string",
        enum: gcnTags,
      },
      uniqueItems: true,
      title: "Tags list",
    };
  }

  const gcnEventFormSchema = {
    type: "object",
    properties,
  };

  return (
    <Form
      schema={gcnEventFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      customValidate={validate}
      liveValidate
    />
  );
};

NewGcnEvent.propTypes = {
  handleClose: PropTypes.func,
};

NewGcnEvent.defaultProps = {
  handleClose: null,
};

export default NewGcnEvent;

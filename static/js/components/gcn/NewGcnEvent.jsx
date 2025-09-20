import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";

import { submitGcnEvent } from "../../ducks/gcnEvent";
import * as gcnTagsActions from "../../ducks/gcnTags";

const NewGcnEvent = ({ handleClose = null }) => {
  const dispatch = useDispatch();
  const gcnTags = [...(useSelector((state) => state.gcnTags) || [])].sort();

  useEffect(() => {
    dispatch(gcnTagsActions.fetchGcnTags());
  }, [dispatch]);

  const handleSubmit = async ({ formData }) => {
    if (formData.json) {
      const parsed_json = dataUriToBuffer(formData.json);
      formData.json = new TextDecoder().decode(parsed_json.buffer);
    }
    if (formData.xml) {
      const parsed_xml = dataUriToBuffer(formData.xml);
      formData.xml = new TextDecoder().decode(parsed_xml.buffer);
    }
    if (formData.ra !== undefined) {
      formData.skymap = {
        ra: formData.ra,
        dec: formData.dec,
        error: formData.error,
      };
    }
    if (formData.polygon) {
      formData.skymap = {
        localization_name: formData.localization_name,
        polygon: formData.polygon,
      };
    }
    const result = await dispatch(submitGcnEvent(formData));
    if (result.status === "success") {
      dispatch(showNotification("GCN Event saved"));
      handleClose?.(); // Call handleClose if it's provided
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
        errors.addError(
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
        errors.addError(
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
      },
      json: {
        type: "string",
        format: "data-url",
        title: "JSON file",
      },
      skymap: {
        type: "string",
        format: "data-url",
        title: "Skymap Fits File",
      },
      ...(gcnTags.length > 0 && {
        tags: {
          type: "array",
          items: {
            type: "string",
            enum: gcnTags,
          },
          uniqueItems: true,
          title: "Tags list",
        },
      }),
    },
  };

  return (
    <Form
      schema={gcnEventFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
      customValidate={validate}
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

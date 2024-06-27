import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import * as spectraActions from "../../ducks/spectra";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const SyntheticPhotometryForm = ({ spectrum_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const { enum_types } = useSelector((state) => state.enum_types);

  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const filters = [...enum_types.ALLOWED_BANDPASSES].sort();

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    const result = await dispatch(
      spectraActions.addSyntheticPhotometry(spectrum_id, formData),
    );
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Synthetic photometry saved"));
    }
  };

  const formSchema = {
    description: "Add Synthetic Photometry",
    type: "object",
    required: ["filters"],
    properties: {
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
      },
    },
  };

  return (
    <div className={classes.container}>
      <div data-testid="tnsrobot-form">
        <Form
          schema={formSchema}
          validator={validator}
          onSubmit={handleSubmit}
          disabled={submissionRequestInProcess}
        />
      </div>
    </div>
  );
};

SyntheticPhotometryForm.propTypes = {
  spectrum_id: PropTypes.number.isRequired,
};

export default SyntheticPhotometryForm;

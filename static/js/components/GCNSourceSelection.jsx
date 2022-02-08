import React from "react";
import { useDispatch } from "react-redux";
import { PropTypes } from "prop-types";
import Form from "@rjsf/material-ui";
import { showNotification } from "baselayer/components/Notifications";
import { fetchGcnEventSources } from "../ducks/sources";

const GCNSourceSelection = ({ gcnEvent }) => {
  const dispatch = useDispatch();
  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(
      fetchGcnEventSources(formData.localizationDateobs, formData)
    );
    if (result.status === "success" && result.data.totalMatches === 0) {
      dispatch(showNotification("No sources found"));
    } else if (result.status === "success") {
      dispatch(showNotification("Event sources modified"));
    }
  };
  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    if (formData.cumulative < 0 || formData.cumulative > 1) {
      errors.cumulative.addError(
        "Value of cumulative should be between 0 and 1"
      );
    }
    return errors;
  }

  const GCNSourceSelectionFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date",
      },
      localizationCumprob: {
        type: "number",
        title: "Cumulative",
        default: 0.95,
      },
      localizationDateobs: {
        type: "string",
        title: "Localization Date Obs.",
        oneOf: gcnEvent.localizations?.map((localization) => ({
          enum: [localization?.dateobs],
          title: `${localization.localization_name} / ${localization?.dateobs}`,
        })),
      },
    },
    required: [
      "startDate",
      "endDate",
      "localizationCumprob",
      "localizationDateobs",
    ],
  };

  return (
    <Form
      schema={GCNSourceSelectionFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
    />
  );
};

GCNSourceSelection.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
  }).isRequired,
};
export default GCNSourceSelection;

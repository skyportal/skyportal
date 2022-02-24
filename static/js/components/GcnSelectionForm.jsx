import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { PropTypes } from "prop-types";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { fetchGcnEventSources } from "../ducks/sources";
import { fetchGcnEventObservations } from "../ducks/observations";
import { fetchGcnEventGalaxies } from "../ducks/galaxies";

const GcnSelectionForm = ({ gcnEvent }) => {
  const dispatch = useDispatch();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    await dispatch(fetchGcnEventSources(gcnEvent.dateobs, formData));
    await dispatch(fetchGcnEventObservations(gcnEvent.dateobs, formData));
    await dispatch(fetchGcnEventGalaxies(gcnEvent.dateobs, formData));
    setIsSubmitting(false);
  };

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    if (
      formData.localizationCumprob < 0 ||
      formData.localizationCumprob > 1.01
    ) {
      errors.cumulative.addError(
        "Value of cumulative should be between 0 and 1"
      );
    }
    return errors;
  }

  const GcnSourceSelectionFormSchema = {
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
        title: "Cumulative Probability",
        default: 0.95,
      },
      localizationName: {
        type: "string",
        title: "Localization Date Obs.",
        oneOf: gcnEvent.localizations?.map((localization) => ({
          enum: [localization?.localization_name],
          title: `${localization.localization_name}`,
        })),
      },
    },
    required: [
      "startDate",
      "endDate",
      "localizationCumprob",
      "localizationName",
    ],
  };

  return (
    <div data-testid="gcnsource-selection-form">
      <Form
        schema={GcnSourceSelectionFormSchema}
        onSubmit={handleSubmit}
        // eslint-disable-next-line react/jsx-no-bind
        validate={validate}
        disabled={isSubmitting}
        liveValidate
      />
      {isSubmitting && (
        <div>
          <CircularProgress />
        </div>
      )}
    </div>
  );
};

GcnSelectionForm.propTypes = {
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
export default GcnSelectionForm;

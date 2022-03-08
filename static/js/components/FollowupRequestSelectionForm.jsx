import React, { useState } from "react";
import { useDispatch } from "react-redux";
import Form from "@rjsf/material-ui";
import CircularProgress from "@material-ui/core/CircularProgress";
import { fetchFollowupRequests } from "../ducks/followup_requests";

const FollowupRequestSelectionForm = () => {
  const dispatch = useDispatch();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    await dispatch(fetchFollowupRequests(formData));
    setIsSubmitting(false);
  };

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    return errors;
  }

  const FollowupRequestSelectionFormSchema = {
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
      sourceID: {
        type: "string",
        title: "Source ID [substrings acceptable]",
      },
      status: {
        type: "string",
        title: "Request status [completed, submitted, etc.]",
      },
    },
  };

  return (
    <div data-testid="gcnsource-selection-form">
      <Form
        schema={FollowupRequestSelectionFormSchema}
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

export default FollowupRequestSelectionForm;

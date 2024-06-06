import React from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";
import { submitMovingObjectHorizons } from "../../ducks/moving_object";
import { fetchMovingObjects } from "../../ducks/moving_objects";

const NewMovingObject = ({ onSubmit }) => {
  const dispatch = useDispatch();

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitMovingObjectHorizons(formData.name));
    if (result.status === "success") {
      dispatch(showNotification("Moving Object saved"));
      dispatch(fetchMovingObjects());
      if (onSubmit) {
        onSubmit();
      }
    } else {
      dispatch(showNotification("Failed to save Moving Object", "error"));
    }
  };

  const movingObjectFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
      },
    },
    required: ["name"],
  };

  return (
    <Form
      schema={movingObjectFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      liveValidate
    />
  );
};

NewMovingObject.propTypes = {
  onSubmit: PropTypes.func,
};

NewMovingObject.defaultProps = {
  onSubmit: null,
};

export default NewMovingObject;

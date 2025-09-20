import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Button from "../Button";
import * as Actions from "../../ducks/source";

const EditFollowupRequestDialog = ({
  followupRequest,
  instrumentFormParams,
  requestType,
  serverSide,
}) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleSubmit = ({ formData }) => {
    const json = {
      allocation_id: followupRequest.allocation.id,
      obj_id: followupRequest.obj_id,
      payload: formData,
    };
    if (serverSide) {
      json.refreshRequests = true;
    }
    dispatch(Actions.editFollowupRequest(json, followupRequest.id));
    handleClose();
  };

  // Since we are editing existing follow-up requests,
  // it makes more sense to set default form values to current request data
  const { formSchema, formSchemaForcedPhotometry } =
    instrumentFormParams[followupRequest.allocation.instrument.id];

  let formCopy;
  // make a copy of the formSchema, so we can modify it
  if (requestType === "triggered") {
    formCopy = JSON.parse(JSON.stringify(formSchema));
  } else {
    formCopy = JSON.parse(JSON.stringify(formSchemaForcedPhotometry));
  }

  Object.keys(formCopy.properties).forEach((key) => {
    // Set the form value for "key" to the value in the existing request's
    // payload, which is the form data sent to the external follow-up API
    if (followupRequest.payload[key]) {
      // if the format is "date" but the value has time info, make sure to only include the date part
      if (
        formCopy.properties[key].format === "date" &&
        followupRequest.payload[key]
      ) {
        formCopy.properties[key].default = followupRequest.payload[key]
          .split("T")[0]
          .split(" ")[0];
      } else {
        formCopy.properties[key].default = followupRequest.payload[key];
      }
    }
  });

  // we do the same for formSchema.dependencies, where each key is a value that has dependencies, under a key called "oneOf"
  // in the oneOf.properties, if any key isnt in formSchema.properties, we set the their default value to the value in the existing request's payload
  if (formCopy?.dependencies) {
    Object.keys(formCopy.dependencies).forEach((key) => {
      formCopy.dependencies[key].oneOf.forEach((oneOf) => {
        Object.keys(oneOf.properties).forEach((oneOfKey) => {
          if (
            !formCopy.properties[oneOfKey] &&
            followupRequest.payload[oneOfKey]
          ) {
            oneOf.properties[oneOfKey].default =
              followupRequest.payload[oneOfKey];
          }
        });
      });
    });
  }

  const validate = (formData, errors) => {
    if (
      formData.start_date &&
      formData.end_date &&
      Date.parse(formData.start_date) > Date.parse(formData.end_date)
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }

    return errors;
  };

  return (
    <span key={followupRequest.id}>
      <Button
        primary
        size="small"
        type="submit"
        onClick={handleClickOpen}
        data-testid={`editRequest_${followupRequest.id}`}
      >
        Edit
      </Button>
      <Dialog open={open} onClose={handleClose}>
        <DialogContent>
          <Form
            schema={formCopy}
            validator={validator}
            uiSchema={
              instrumentFormParams[followupRequest.allocation.instrument.id]
                .uiSchema
            }
            onSubmit={handleSubmit}
            customValidate={validate}
            liveValidate
          />
        </DialogContent>
      </Dialog>
    </span>
  );
};

EditFollowupRequestDialog.propTypes = {
  followupRequest: PropTypes.shape({
    requester: PropTypes.shape({
      id: PropTypes.number,
      username: PropTypes.string,
    }),
    allocation: PropTypes.shape({
      instrument: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
      id: PropTypes.number,
    }),
    start_date: PropTypes.string,
    end_date: PropTypes.string,
    priority: PropTypes.string,
    status: PropTypes.string,
    obj_id: PropTypes.string,
    id: PropTypes.number,
    payload: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
  }).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    uiSchema: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    implementedMethods: PropTypes.objectOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
  }).isRequired,
  requestType: PropTypes.string,
  serverSide: PropTypes.bool,
};

EditFollowupRequestDialog.defaultProps = {
  requestType: "triggered",
  serverSide: false,
};

export default EditFollowupRequestDialog;

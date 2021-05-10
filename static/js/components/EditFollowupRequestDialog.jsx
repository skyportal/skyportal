import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import Button from "@material-ui/core/Button";
import { makeStyles } from "@material-ui/core/styles";
import Form from "@rjsf/material-ui";
import * as Actions from "../ducks/source";

const useStyles = makeStyles(() => ({
  dialog: {
    position: "fixed",
  },
}));

const EditFollowupRequestDialog = ({
  followupRequest,
  instrumentFormParams,
}) => {
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const classes = useStyles();

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
    dispatch(Actions.editFollowupRequest(json, followupRequest.id));
    handleClose();
  };

  // Since we are editing exsiting follow-up requests,
  // it makes more sense to set default form values to current request data
  const { formSchema } = instrumentFormParams[
    followupRequest.allocation.instrument.id
  ];
  Object.keys(formSchema.properties).forEach((key) => {
    // Set the form value for "key" to the value in the existing request's
    // payload, which is the form data sent to the external follow-up API
    formSchema.properties[key].default = followupRequest.payload[key];
  });

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
        size="small"
        color="primary"
        type="submit"
        variant="outlined"
        onClick={handleClickOpen}
        data-testid={`editRequest_${followupRequest.id}`}
      >
        Edit
      </Button>
      <Dialog open={open} onClose={handleClose} className={classes.dialog}>
        <DialogContent>
          <Form
            schema={formSchema}
            uiSchema={
              instrumentFormParams[followupRequest.allocation.instrument.id]
                .uiSchema
            }
            onSubmit={handleSubmit}
            validate={validate}
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
    payload: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
  instrumentFormParams: PropTypes.shape({
    formSchema: PropTypes.objectOf(PropTypes.any),
    uiSchema: PropTypes.objectOf(PropTypes.any),
    implementedMethods: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
};

export default EditFollowupRequestDialog;

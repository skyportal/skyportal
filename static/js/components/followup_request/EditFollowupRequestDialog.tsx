import React, { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import * as Actions from "../../ducks/source";

interface EditFollowupRequestDialogProps {
  followupRequest: {
    requester?: {
      id?: number;
      username?: string;
    };
    allocation: {
      instrument: {
        id?: number;
        name?: string;
      };
      id?: number;
    };
    start_date?: string;
    end_date?: string;
    priority?: string;
    status?: string;
    obj_id?: string;
    id?: number;
    payload?: Record<string, any>;
  };
  instrumentFormParams: Record<string, any>;
  requestType?: string;
  serverSide?: boolean;
}

const EditFollowupRequestDialog = ({
  followupRequest,
  instrumentFormParams,
  requestType = "triggered",
  serverSide = false,
}: EditFollowupRequestDialogProps) => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleSubmit = ({ formData }: { formData: any }) => {
    if (followupRequest.id === undefined) {
      return;
    }
    const json: any = {
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
    instrumentFormParams[followupRequest.allocation.instrument.id as number];

  let formCopy: any;
  // make a copy of the formSchema, so we can modify it
  if (requestType === "triggered") {
    formCopy = JSON.parse(JSON.stringify(formSchema));
  } else {
    formCopy = JSON.parse(JSON.stringify(formSchemaForcedPhotometry));
  }

  Object.keys(formCopy.properties).forEach((key) => {
    // Set the form value for "key" to the value in the existing request's
    // payload, which is the form data sent to the external follow-up API
    if (followupRequest.payload?.[key]) {
      // if the format is "date" but the value has time info, make sure to only include the date part
      if (
        formCopy.properties[key].format === "date" &&
        followupRequest.payload?.[key]
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
      formCopy.dependencies[key].oneOf.forEach((oneOf: any) => {
        Object.keys(oneOf.properties).forEach((oneOfKey) => {
          if (
            !formCopy.properties[oneOfKey] &&
            followupRequest.payload?.[oneOfKey]
          ) {
            oneOf.properties[oneOfKey].default =
              followupRequest.payload[oneOfKey];
          }
        });
      });
    });
  }

  const validate = (formData: any, errors: any) => {
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
              instrumentFormParams[
                followupRequest.allocation.instrument.id as number
              ].uiSchema
            }
            onSubmit={handleSubmit as any}
            customValidate={validate}
            liveValidate
          />
        </DialogContent>
      </Dialog>
    </span>
  );
};

export default EditFollowupRequestDialog;

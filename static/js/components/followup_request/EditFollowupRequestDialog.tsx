import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { useEditFollowupRequestMutation } from "../../ducks/source";
import { localeSafeFields } from "./LocaleSafeNumberField";
import DialogTitle from "@mui/material/DialogTitle";

interface EditFollowupRequestDialogProps {
  followupRequest: {
    id: number;
    obj_id: string;
    allocation: { id: number; instrument: { id: number } };
    payload?: Record<string, any>;
  };
  instrumentFormParams: Record<string, any>;
  onClose: () => void;
  requestType?: string;
  serverSide?: boolean;
}

const EditFollowupRequestDialog = ({
  followupRequest,
  instrumentFormParams,
  onClose,
  requestType = "triggered",
  serverSide = false,
}: EditFollowupRequestDialogProps) => {
  const [editFollowupRequestMutation] = useEditFollowupRequestMutation();
  const formParams =
    instrumentFormParams[followupRequest.allocation.instrument.id];

  const handleSubmit = ({ formData }: { formData: any }) => {
    const json: any = {
      allocation_id: followupRequest.allocation.id,
      obj_id: followupRequest.obj_id,
      payload: formData,
    };
    if (serverSide) {
      json.refreshRequests = true;
    }
    editFollowupRequestMutation({
      params: json,
      requestID: followupRequest.id,
    });
    onClose();
  };

  const formCopy = JSON.parse(
    JSON.stringify(
      requestType === "triggered"
        ? formParams.formSchema
        : formParams.formSchemaForcedPhotometry,
    ),
  );

  Object.keys(formCopy.properties).forEach((key) => {
    if (followupRequest.payload?.[key]) {
      // a "date" field can carry time info, which the date widget rejects
      if (formCopy.properties[key].format === "date") {
        formCopy.properties[key].default = followupRequest.payload[key]
          .split("T")[0]
          .split(" ")[0];
      } else {
        formCopy.properties[key].default = followupRequest.payload[key];
      }
    }
  });

  Object.keys(formCopy.dependencies || {}).forEach((key) => {
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
    <Dialog open onClose={onClose}>
      <DialogTitle>Edit Follow-up Request</DialogTitle>
      <DialogContent>
        <Form
          schema={formCopy}
          validator={validator}
          uiSchema={formParams.uiSchema}
          fields={localeSafeFields}
          onSubmit={handleSubmit as any}
          customValidate={validate}
          liveValidate
        />
      </DialogContent>
    </Dialog>
  );
};

export default EditFollowupRequestDialog;

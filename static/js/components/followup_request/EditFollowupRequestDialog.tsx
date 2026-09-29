import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { useEditFollowupRequestMutation } from "../../ducks/source";
import { localeSafeFields } from "./LocaleSafeNumberField";

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
  refresh?: boolean;
}

const EditFollowupRequestDialog = ({
  followupRequest,
  instrumentFormParams,
  onClose,
  requestType = "triggered",
  refresh = false,
}: EditFollowupRequestDialogProps) => {
  const [editFollowupRequestMutation] = useEditFollowupRequestMutation();
  const { payload = {} } = followupRequest;
  const formParams =
    instrumentFormParams[followupRequest.allocation.instrument.id];

  const handleSubmit = ({ formData }: { formData?: any }) => {
    editFollowupRequestMutation({
      params: {
        allocation_id: followupRequest.allocation.id,
        obj_id: followupRequest.obj_id,
        payload: formData,
        ...(refresh && { refreshRequests: true }),
      },
      requestID: followupRequest.id,
    });
    onClose();
  };

  const schema = structuredClone(
    requestType === "triggered"
      ? formParams.formSchema
      : formParams.formSchemaForcedPhotometry,
  );
  Object.entries(schema.properties).forEach(
    ([key, property]: [string, any]) => {
      if (!payload[key]) return;
      property.default =
        property.format === "date"
          ? payload[key].split("T")[0].split(" ")[0]
          : payload[key];
    },
  );
  Object.values(schema.dependencies ?? {}).forEach((dependency: any) =>
    dependency.oneOf.forEach((option: any) =>
      Object.entries(option.properties).forEach(
        ([key, property]: [string, any]) => {
          if (!schema.properties[key] && payload[key])
            property.default = payload[key];
        },
      ),
    ),
  );

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
          schema={schema}
          validator={validator}
          uiSchema={formParams.uiSchema}
          fields={localeSafeFields}
          onSubmit={handleSubmit}
          customValidate={validate}
          liveValidate
        />
      </DialogContent>
    </Dialog>
  );
};

export default EditFollowupRequestDialog;

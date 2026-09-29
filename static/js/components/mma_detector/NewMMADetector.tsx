import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import {
  useGetMMADetectorsQuery,
  useSubmitMMADetectorMutation,
} from "../../ducks/mmadetector";

const schema = {
  type: "object",
  properties: {
    name: { type: "string", title: "Name" },
    nickname: { type: "string", title: "Nickname (e.g., P200)" },
    type: {
      type: "string",
      oneOf: [
        { enum: ["gravitational-wave"], title: "Gravitational Wave" },
        { enum: ["neutrino"], title: "Neutrino" },
        { enum: ["gamma-ray-burst"], title: "Gamma-ray Burst" },
      ],
      title: "Type",
    },
    lat: { type: "number", title: "Latitude [deg]" },
    lon: { type: "number", title: "Longitude [deg]" },
    fixed_location: {
      type: "boolean",
      title: "Does this telescope have a fixed location (lon, lat)?",
    },
  },
  required: ["name", "nickname", "type", "fixed_location"],
};

const uiSchema = {
  fixed_location: { "ui:widget": "radio", "ui:labels": ["Yes", "No"] },
};

const NewMMADetector = () => {
  const { data: mmadetectors = [] } = useGetMMADetectorsQuery();
  const dispatch = useAppDispatch();
  const [submitMMADetector] = useSubmitMMADetectorMutation();

  const handleSubmit = async ({ formData }: any) => {
    try {
      await submitMMADetector(formData).unwrap();
      dispatch(showNotification("MMADetector saved"));
    } catch {
      // error notification handled by the API base query
    }
  };

  const validate = (formData: any, errors: any) => {
    if (mmadetectors.some(({ name }: any) => name === formData.name)) {
      errors.name.addError("MMADetector name matches another, please change.");
    }
    if (formData.lon < -180 || formData.lon > 180) {
      errors.lon.addError("Longitude must be between -180 and 180.");
    }
    if (formData.lat < -90 || formData.lat > 90) {
      errors.lat.addError("Latitude must be between -90 and 90.");
    }
    return errors;
  };

  return (
    <Form
      schema={schema as any}
      validator={validator}
      uiSchema={uiSchema}
      onSubmit={handleSubmit}
      customValidate={validate}
    />
  );
};

export default NewMMADetector;

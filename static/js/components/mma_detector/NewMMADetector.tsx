import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import {
  useGetMMADetectorsQuery,
  useSubmitMMADetectorMutation,
} from "../../ducks/mmadetector";

const NewMMADetector = () => {
  const { data: mmadetectorList } = useGetMMADetectorsQuery();
  const dispatch = useAppDispatch();
  const [submitMMADetector] = useSubmitMMADetectorMutation();

  const handleSubmit = async ({ formData }: { formData: any }) => {
    try {
      await submitMMADetector(formData).unwrap();
      dispatch(showNotification("MMADetector saved"));
    } catch {
      // error notification handled by the API base query
    }
  };

  const uiSchema = {
    fixed_location: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
  };

  function validate(formData: any, errors: any) {
    mmadetectorList?.forEach((mmadetector: any) => {
      if (formData.name === mmadetector.name) {
        errors.name.addError(
          "MMADetector name matches another, please change.",
        );
      }
    });
    if (formData.lon < -180 || formData.lon > 180) {
      errors.lon.addError("Longitude must be between -180 and 180.");
    }
    if (formData.lat < -90 || formData.lat > 90) {
      errors.lat.addError("Latitude must be between -90 and 90.");
    }

    return errors;
  }

  const mmadetectorFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
      },
      nickname: {
        type: "string",
        title: "Nickname (e.g., P200)",
      },
      type: {
        type: "string",
        oneOf: [
          { enum: ["gravitational-wave"], title: "Gravitational Wave" },
          { enum: ["neutrino"], title: "Neutrino" },
          { enum: ["gamma-ray-burst"], title: "Gamma-ray Burst" },
        ],
        title: "Type",
      },
      lat: {
        type: "number",
        title: "Latitude [deg]",
      },
      lon: {
        type: "number",
        title: "Longitude [deg]",
      },
      fixed_location: {
        type: "boolean",
        title: "Does this telescope have a fixed location (lon, lat)?",
      },
    },
    required: ["name", "nickname", "type", "fixed_location"],
  };

  return (
    <Form
      schema={mmadetectorFormSchema as any}
      validator={validator}
      uiSchema={uiSchema}
      onSubmit={handleSubmit as any}
      customValidate={validate}
    />
  );
};

export default NewMMADetector;

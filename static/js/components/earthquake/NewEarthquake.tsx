import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useSubmitEarthquakeMutation } from "../../ducks/earthquake";

dayjs.extend(utc);

const validate = (formData: any, errors: any) => {
  if (formData.longitude < -180 || formData.longitude > 180) {
    errors.longitude.addError("Longitude must be between -180 and 180.");
  }
  if (formData.latitude < -90 || formData.latitude > 90) {
    errors.latitude.addError("Latitude must be between -90 and 90.");
  }
  return errors;
};

const NewEarthquake = () => {
  const dispatch = useAppDispatch();
  const [submitEarthquake] = useSubmitEarthquakeMutation();

  const handleSubmit = async ({ formData }: any) => {
    try {
      await submitEarthquake(formData).unwrap();
      dispatch(showNotification("Earthquake saved"));
    } catch {
      // error notification handled by the base query
    }
  };

  const schema = {
    type: "object",
    properties: {
      event_id: { type: "string", title: "Name" },
      date: {
        type: "string",
        title: "Date (UTC)",
        default: dayjs().utc().format("YYYY-MM-DDTHH:mm:ss"),
      },
      latitude: { type: "number", title: "Latitude [deg]" },
      longitude: { type: "number", title: "Longitude [deg]" },
      depth: { type: "number", title: "Depth [m]" },
      magnitude: { type: "number", title: "Magnitude" },
    },
    required: [
      "event_id",
      "date",
      "latitude",
      "longitude",
      "depth",
      "magnitude",
    ],
  };

  return (
    <Form
      schema={schema as any}
      validator={validator}
      onSubmit={handleSubmit}
      customValidate={validate}
    />
  );
};

export default NewEarthquake;

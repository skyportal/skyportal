import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { useAppDispatch } from "../types/hooks";
import { useSubmitRecurringAPIMutation } from "../ducks/recurring_apis";
import { useGetConfigQuery } from "../ducks/config";

dayjs.extend(utc);

const NewRecurringAPI = () => {
  const dispatch = useAppDispatch();
  const [submitRecurringAPI] = useSubmitRecurringAPIMutation();
  const defaultDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const allowedRecurringAPIMethods = (useGetConfigQuery().data as any)
    ?.allowedRecurringAPIMethods;

  const handleSubmit = async ({ formData }: { formData: any }) => {
    formData.next_call = formData.next_call
      .replace("+00:00", "")
      .replace(".000Z", "");
    try {
      await submitRecurringAPI(formData).unwrap();
      dispatch(showNotification("RecurringAPI saved"));
    } catch {
      // error notification handled by the base query
    }
  };

  const analysisServiceFormSchema = {
    type: "object",
    properties: {
      endpoint: {
        type: "string",
        title: "Endpoint names",
      },
      method: {
        type: "string",
        oneOf: allowedRecurringAPIMethods.map(
          (allowedRecurringAPIMethod: string) => ({
            enum: [allowedRecurringAPIMethod],
            title: allowedRecurringAPIMethod,
          }),
        ),
        title: "HTTP Method",
        default: allowedRecurringAPIMethods[0],
      },
      next_call: {
        type: "string",
        format: "date-time",
        title: "Date",
        default: defaultDate,
      },
      call_delay: {
        type: "number",
        title: "Delay between reminders (in days)",
        default: 1,
      },
      payload: {
        type: "string",
        title: 'API data (i.e. {"allocation_id": 1}',
      },
    },
    required: ["endpoint", "method", "next_call", "call_delay", "payload"],
  };

  return (
    <div>
      <Form
        schema={analysisServiceFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
        liveValidate
      />
    </div>
  );
};

export default NewRecurringAPI;

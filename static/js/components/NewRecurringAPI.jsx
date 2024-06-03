import React from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import {
  fetchRecurringAPIs,
  submitRecurringAPI,
} from "../ducks/recurring_apis";

dayjs.extend(utc);

const NewRecurringAPI = () => {
  const dispatch = useDispatch();
  const defaultDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const allowedRecurringAPIMethods = useSelector(
    (state) => state.config.allowedRecurringAPIMethods,
  );

  const handleSubmit = async ({ formData }) => {
    formData.next_call = formData.next_call
      .replace("+00:00", "")
      .replace(".000Z", "");
    const result = await dispatch(submitRecurringAPI(formData));
    if (result.status === "success") {
      dispatch(showNotification("RecurringAPI saved"));
      dispatch(fetchRecurringAPIs());
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
        oneOf: allowedRecurringAPIMethods.map((allowedRecurringAPIMethod) => ({
          enum: [allowedRecurringAPIMethod],
          title: allowedRecurringAPIMethod,
        })),
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
        schema={analysisServiceFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        liveValidate
      />
    </div>
  );
};

export default NewRecurringAPI;

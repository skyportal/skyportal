import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Paper from "../Paper";
import { submitObservingRun } from "../../ducks/observingRun";

dayjs.extend(utc);

const NewObservingRun = () => {
  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { telescopeList } = useAppSelector((state) => state["telescopes"]);
  const groups = useAppSelector((state) => state.groups.userAccessible);
  const dispatch = useAppDispatch();

  const handleSubmit = async ({ formData }: { formData: any }) => {
    if (formData.group_id === -1) {
      delete formData.group_id;
    }
    const result: any = await dispatch(submitObservingRun(formData));
    if (result.status === "success") {
      dispatch(showNotification("Observing run saved"));
    }
  };

  const observingRunFormSchema = {
    type: "object",
    properties: {
      pi: {
        type: "string",
        title: "PI",
      },
      calendar_date: {
        type: "string",
        format: "date",
        title: "Calendar Date",
        default: dayjs().utc().format("YYYY-MM-DD"),
      },
      duration: {
        type: "number",
        title: "Number of nights",
        default: 1,
      },
      observers: {
        type: "string",
        title: "Observers",
      },
      instrument_id: {
        type: "integer",
        oneOf: instrumentList.map((instrument: any) => ({
          enum: [instrument.id],
          title: `${
            telescopeList.find(
              (telescope: any) => telescope.id === instrument.telescope_id,
            )?.name
          } / ${instrument.name}`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
      group_id: {
        type: "integer",
        oneOf: [{ enum: [-1], title: "No group" }].concat(
          groups.map((group: any) => ({
            enum: [group.id],
            title: group.name,
          })),
        ),
        default: -1,
        title: "Group",
      },
    },
    required: ["pi", "calendar_date", "instrument_id"],
  };

  return (
    <Paper>
      <Typography variant="h6">Add a New Observing Run</Typography>
      <Form
        schema={observingRunFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
      />
    </Paper>
  );
};

export default NewObservingRun;

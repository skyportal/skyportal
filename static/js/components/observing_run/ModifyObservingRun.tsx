import { useMemo } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { modifyObservingRun } from "../../ducks/observingRun";
import { useAppDispatch, useAppSelector } from "../../types/hooks";

dayjs.extend(utc);

interface ModifyObservingRunProps {
  run_id?: number | null;
  onClose?: (() => void) | null;
}

const ModifyObservingRun = ({
  run_id,
  onClose = null,
}: ModifyObservingRunProps) => {
  const { observingRunList } = useAppSelector(
    (state) => state["observingRuns"],
  );
  const groups = useAppSelector((state) => state.groups.userAccessible);
  const dispatch = useAppDispatch();

  const formData = useMemo(() => {
    const run = observingRunList.find((r: any) => r?.id === run_id);
    if (!run) return null;
    return {
      pi: run.pi,
      calendar_date: dayjs(`${run.run_end_utc}Z`).utc().format("YYYY-MM-DD"),
      duration: run.duration,
      observers: run.observers,
      group_id: run.group_id ?? -1,
    };
  }, [run_id, observingRunList]);

  if (!run_id || !formData) return null;

  const handleSubmit = async ({ formData: submitted }: { formData: any }) => {
    const payload = { ...submitted };
    if (payload.group_id === -1) {
      delete payload.group_id;
    }
    const result: any = await dispatch(modifyObservingRun(run_id, payload));
    if (result.status === "success") {
      dispatch(showNotification("Observing run updated"));
      if (onClose) onClose();
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
      },
      duration: {
        type: "number",
        title: "Number of nights",
      },
      observers: {
        type: "string",
        title: "Observers",
      },
      group_id: {
        type: "integer",
        title: "Group",
        oneOf: [{ enum: [-1], title: "No group" }].concat(
          groups.map((group: any) => ({
            enum: [group.id],
            title: group.name,
          })),
        ),
      },
    },
    required: ["pi", "calendar_date"],
  };

  return (
    <Form
      key={run_id}
      schema={observingRunFormSchema as any}
      formData={formData}
      validator={validator}
      onSubmit={handleSubmit as any}
    />
  );
};

export default ModifyObservingRun;

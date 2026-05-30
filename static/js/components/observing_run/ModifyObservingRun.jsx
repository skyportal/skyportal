import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { modifyObservingRun } from "../../ducks/observingRun";

dayjs.extend(utc);

const ModifyObservingRun = ({ run_id, onClose }) => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();

  const formData = useMemo(() => {
    const run = observingRunList.find((r) => r?.id === run_id);
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

  const handleSubmit = async ({ formData: submitted }) => {
    const payload = { ...submitted };
    if (payload.group_id === -1) {
      delete payload.group_id;
    }
    const result = await dispatch(modifyObservingRun(run_id, payload));
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
          groups.map((group) => ({ enum: [group.id], title: group.name })),
        ),
      },
    },
    required: ["pi", "calendar_date"],
  };

  return (
    <Form
      key={run_id}
      schema={observingRunFormSchema}
      formData={formData}
      validator={validator}
      onSubmit={handleSubmit}
    />
  );
};

ModifyObservingRun.propTypes = {
  run_id: PropTypes.number,
  onClose: PropTypes.func,
};

ModifyObservingRun.defaultProps = {
  onClose: null,
};

export default ModifyObservingRun;

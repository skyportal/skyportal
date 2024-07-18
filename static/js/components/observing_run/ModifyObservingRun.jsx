import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import {
  submitObservingRun,
  modifyObservingRun,
} from "../../ducks/observingRun";

dayjs.extend(utc);

const ModifyObservingRun = ({ run_id, onClose }) => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const groups = useSelector((state) => state.groups.userAccessible);
  const dispatch = useDispatch();

  const [defaultDate, setDefaultDate] = useState(
    dayjs().utc().format("YYYY-MM-DD"),
  );
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [PI, setPI] = useState(null);
  const [observers, setObservers] = useState(null);
  const [duration, setDuration] = useState(null);

  useEffect(() => {
    const selectedObservingRun = observingRunList.find(
      (observingRun) => observingRun?.id === run_id,
    );
    if (selectedObservingRun) {
      const currentGroup =
        groups.find((g) => g.id === selectedObservingRun.group_id) || null;

      setSelectedGroup(currentGroup);
      setDefaultDate(
        dayjs(`${selectedObservingRun.run_end_utc}Z`)
          .utc()
          .format("YYYY-MM-DD"),
      );
      setPI(selectedObservingRun.pi);
      setObservers(selectedObservingRun.observers);
      setDuration(selectedObservingRun.duration);
    }
  }, [run_id, observingRunList]);

  const handleSubmit = async ({ formData }) => {
    if (formData.group_id === -1) {
      delete formData.group_id;
    }
    const result = await dispatch(modifyObservingRun(run_id, formData));
    if (result.status === "success") {
      dispatch(showNotification("Observing run updated"));
    }
  };

  const observingRunFormSchema = {
    type: "object",
    properties: {
      pi: {
        type: "string",
        title: "PI",
        default: PI,
      },
      calendar_date: {
        type: "string",
        format: "date",
        title: "Calendar Date",
        default: defaultDate,
      },
      duration: {
        type: "string",
        title: "Number of nights",
        default: duration,
      },
      observers: {
        type: "string",
        title: "Observers",
        default: observers,
      },
      group_id: {
        type: "integer",
        oneOf: [{ enum: [-1], title: "No group" }].concat(
          groups.map((group) => ({ enum: [group.id], title: group.name })),
        ),
        default: selectedGroup?.id,
        title: "Group",
      },
    },
    required: ["pi", "calendar_date"],
  };

  return (
    <Form
      schema={observingRunFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
    />
  );
};

ModifyObservingRun.propTypes = {
  run_id: PropTypes.number.isRequired,
  onClose: PropTypes.func,
};

ModifyObservingRun.defaultProps = {
  onClose: null,
};

export default ModifyObservingRun;

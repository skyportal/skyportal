import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import * as queuedObservationActions from "../../ducks/queued_observations";
import * as allocationActions from "../../ducks/allocations";

dayjs.extend(utc);

const NewAPIQueuedObservation = ({ onClose }) => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useSelector(
    (state) => state.allocations,
  );
  const allGroups = useSelector((state) => state.groups.all);

  const dispatch = useDispatch();

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      await dispatch(
        allocationActions.fetchAllocationsApiObsplan({
          apiImplements: "queued",
        }),
      );
    };

    getAllocations();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
  }, [dispatch]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return <h3>No telescopes/instruments available...</h3>;
  }

  if (allocationListApiObsplan.length === 0) {
    return <h3>No allocations with an observation plan API...</h3>;
  }

  const groupLookUp = {};

  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};

  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp = {};

  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSubmit = async ({ formData }) => {
    const data = {
      startDate: formData.start_date.replace("+00:00", "").replace(".000Z", ""),
      endDate: formData.end_date.replace("+00:00", "").replace(".000Z", ""),
    };
    const result = await dispatch(
      queuedObservationActions.requestAPIQueuedObservations(
        formData.allocation_id,
        data,
      ),
    );
    if (result.status === "success") {
      dispatch(
        showNotification(
          "Requested API Queued Observation, the list will update shortly.",
        ),
      );
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  function validate(formData, errors) {
    if (nowDate > formData.start_date) {
      errors.end_date.addError(
        "Start date must be after current time, please fix.",
      );
    }
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix.",
      );
    }
    return errors;
  }

  const observationFormSchema = {
    type: "object",
    properties: {
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date (Local Time)",
        default: defaultStartDate,
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date (Local Time)",
        default: defaultEndDate,
      },
      allocation_id: {
        type: "integer",
        oneOf: allocationListApiObsplan.map((allocation) => ({
          enum: [allocation.id],
          title: `${
            telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
          } / ${instLookUp[allocation.instrument_id].name} - ${
            groupLookUp[allocation.group_id]?.name
          } (PI ${allocation.pi})`,
        })),
        title: "Allocation",
        default: allocationListApiObsplan[0]?.id,
      },
    },
    required: ["start_date", "end_date", "allocation_id"],
  };

  return (
    <Form
      schema={observationFormSchema}
      validator={validator}
      onSubmit={handleSubmit}
      customValidate={validate}
      liveValidate
    />
  );
};

NewAPIQueuedObservation.propTypes = {
  onClose: PropTypes.func,
};

NewAPIQueuedObservation.defaultProps = {
  onClose: null,
};

export default NewAPIQueuedObservation;

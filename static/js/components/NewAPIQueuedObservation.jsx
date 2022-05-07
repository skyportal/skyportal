import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as queuedObservationActions from "../ducks/queued_observations";
import * as allocationActions from "../ducks/allocations";
import * as instrumentActions from "../ducks/instruments";

dayjs.extend(utc);

const NewAPIQueuedObservation = () => {
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);
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
        allocationActions.fetchAllocations({
          apiType: "api_classname_obsplan",
        })
      );
    };

    getAllocations();

    dispatch(
      instrumentActions.fetchInstrumentForms({
        apiType: "api_classname_obsplan",
      })
    );
    dispatch(
      allocationActions.fetchAllocations({
        apiType: "api_classname_obsplan",
      })
    );

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return <h3>No telescopes/instruments available...</h3>;
  }

  if (allocationList.length === 0) {
    return <h3>No robotic instruments available...</h3>;
  }

  const groupLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allGroups?.forEach((group) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSubmit = async ({ formData }) => {
    const data = {
      startDate: formData.start_date.replace("+00:00", ""),
      endDate: formData.end_date.replace("+00:00", ""),
    };
    await dispatch(
      queuedObservationActions.requestAPIQueuedObservations(
        formData.allocation_id,
        data
      )
    );
  };

  function validate(formData, errors) {
    if (nowDate > formData.start_date) {
      errors.end_date.addError(
        "Start date must be after current time, please fix."
      );
    }
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
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
        oneOf: allocationList.map((allocation) => ({
          enum: [allocation.id],
          title: `${
            telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
          } / ${instLookUp[allocation.instrument_id].name} - ${
            groupLookUp[allocation.group_id].name
          } (PI ${allocation.pi})`,
        })),
        title: "Allocation",
        default: allocationList[0]?.id,
      },
    },
    required: ["start_date", "end_date", "allocation_id"],
  };

  return (
    <Form
      schema={observationFormSchema}
      onSubmit={handleSubmit}
      // eslint-disable-next-line react/jsx-no-bind
      validate={validate}
      liveValidate
    />
  );
};

export default NewAPIQueuedObservation;

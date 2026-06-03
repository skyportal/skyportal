import { useEffect } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppSelector, useAppDispatch } from "../../types/hooks";
import * as observationActions from "../../ducks/observations";
import * as allocationActions from "../../ducks/allocations";

dayjs.extend(utc);

interface NewAPIObservationProps {
  onClose?: (() => void) | null;
}

const NewAPIObservation = ({ onClose = null }: NewAPIObservationProps) => {
  const { instrumentList } = useAppSelector((state) => state.instruments);
  const { telescopeList } = useAppSelector((state) => state.telescopes);
  const { allocationListApiObsplan } = useAppSelector(
    (state) => state.allocations,
  ) as any;
  const allGroups = useAppSelector((state) => state.groups.all);

  const dispatch = useAppDispatch();

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultStartDate = dayjs()
    .subtract(3, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  useEffect(() => {
    const getAllocations = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update
      await dispatch(
        allocationActions.fetchAllocationsApiObsplan({
          apiImplements: "retrieve",
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

  const groupLookUp: any = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: any = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp: any = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSubmit = async ({ formData }: { formData: any }) => {
    formData.start_date = formData.start_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.end_date = formData.end_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    const result = (await dispatch(
      observationActions.requestAPIObservations(formData),
    )) as any;
    if (result.status === "success") {
      dispatch(
        showNotification(
          "Requested API Executed Observation, the list will update shortly.",
        ),
      );
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  function validate(formData: any, errors: any) {
    if (nowDate < formData.end_date) {
      errors.end_date.addError(
        "End date must be before current time, please fix.",
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
        oneOf: allocationListApiObsplan.map((allocation: any) => ({
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
      schema={observationFormSchema as any}
      validator={validator}
      onSubmit={handleSubmit as any}
      customValidate={validate}
      liveValidate
    />
  );
};

export default NewAPIObservation;

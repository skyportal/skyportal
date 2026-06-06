import { useGetGroupsQuery } from "../../ducks/groups";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import * as queuedObservationActions from "../../ducks/queued_observations";
import { useGetAllocationsApiObsplanQuery } from "../../ducks/allocations";

dayjs.extend(utc);

interface NewAPIQueuedObservationProps {
  onClose?: (() => void) | null;
}

const NewAPIQueuedObservation = ({
  onClose = null,
}: NewAPIQueuedObservationProps) => {
  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery({
      apiImplements: "queued",
    });
  const allGroups = useGetGroupsQuery().data?.all ?? null;

  const dispatch = useAppDispatch();

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

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

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp: Record<string, any> = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const data = {
      startDate: formData.start_date.replace("+00:00", "").replace(".000Z", ""),
      endDate: formData.end_date.replace("+00:00", "").replace(".000Z", ""),
    };
    const result: any = await dispatch(
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

  function validate(formData: any, errors: any) {
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
        oneOf: allocationListApiObsplan.map((allocation: any) => ({
          enum: [allocation.id],
          title: `${
            telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
          } / ${instLookUp[allocation.instrument_id].name} - ${
            groupLookUp[allocation.group_id]?.name
          } (PI ${allocation.pi})`,
        })),
        title: "Allocation",
        default: allocationListApiObsplan[0]?.["id"],
      },
    },
    required: ["start_date", "end_date", "allocation_id"],
  };

  return (
    <Form
      schema={observationFormSchema as any}
      validator={validator}
      onSubmit={handleSubmit as any}
      customValidate={validate as any}
      liveValidate
    />
  );
};

export default NewAPIQueuedObservation;

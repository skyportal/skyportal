import { useGetGroupsQuery } from "../../ducks/groups";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useRequestAPIObservationsMutation } from "../../ducks/observations";
import { useGetAllocationsApiObsplanQuery } from "../../ducks/allocations";
import { useGetInstrumentsQuery } from "../../ducks/instruments";

dayjs.extend(utc);

interface NewAPIObservationProps {
  onClose?: (() => void) | null;
}

const NewAPIObservation = ({ onClose = null }: NewAPIObservationProps) => {
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiObsplan = [] } =
    useGetAllocationsApiObsplanQuery({
      apiImplements: "retrieve",
    });
  const allGroups = useGetGroupsQuery().data?.all ?? null;

  const dispatch = useAppDispatch();
  const [requestAPIObservations] = useRequestAPIObservationsMutation();

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultStartDate = dayjs()
    .subtract(3, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

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
    try {
      await requestAPIObservations(formData).unwrap();
      dispatch(
        showNotification(
          "Requested API Executed Observation, the list will update shortly.",
        ),
      );
      if (typeof onClose === "function") {
        onClose();
      }
    } catch {
      // error notification handled by the baseQuery
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
      customValidate={validate}
      liveValidate
    />
  );
};

export default NewAPIObservation;

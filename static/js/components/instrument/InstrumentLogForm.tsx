import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useState } from "react";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { useAppDispatch } from "../../types/hooks";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import * as instrumentLogActions from "../../ducks/instrument_log";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  allocationSelect: {
    width: "100%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
    "& > *": {
      marginTop: "1rem",
      marginBottom: "1rem",
    },
  },
}));

interface InstrumentLogFormProps {
  instrument: {
    id: number;
    name?: string;
    [key: string]: any;
  };
}

const InstrumentLogForm = ({ instrument }: InstrumentLogFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery({ instrument_id: instrument.id });
  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const defaultStartDate = dayjs
    .utc()
    .subtract(2, "day")
    .format("YYYY-MM-DD HH:mm:ss");
  const defaultEndDate = dayjs.utc().format("YYYY-MM-DD HH:mm:ss");

  useEffect(() => {
    if (allocationListApiClassname?.length > 0) {
      setSelectedAllocationId(allocationListApiClassname[0]?.["id"]);
    }
  }, [allocationListApiClassname]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiClassname is not
  // empty.
  if (allocationListApiClassname.length === 0 || !selectedAllocationId) {
    return <h3>No allocations with a follow-up API...</h3>;
  }

  const groupLookUp: Record<number, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const allocationLookUp: Record<number, any> = {};

  allocationListApiClassname?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setIsSubmitting(true);
    formData.startDate = formData.startDate
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.endDate = formData.endDate
      .replace("+00:00", "")
      .replace(".000Z", "");

    await dispatch(
      instrumentLogActions.fetchInstrumentLogExternal(
        selectedAllocationId,
        formData,
      ),
    );

    setIsSubmitting(false);
  };

  const validate = (formData: any, errors: any) => {
    if (
      formData.start_date &&
      formData.end_date &&
      formData.start_date > formData.end_date
    ) {
      errors.start_date.addError("Start Date must come before End Date");
    }

    return errors;
  };

  const handleSelectedAllocationChange = (e: any) => {
    setSelectedAllocationId(e.target.value);
  };

  const InstrumentLogSelectionFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date",
        default: defaultEndDate,
      },
    },
    required: ["startDate", "endDate"],
  };

  return (
    <div className={classes.container}>
      <div>
        <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="allocationSelectLabel"
          value={selectedAllocationId}
          onChange={handleSelectedAllocationChange}
          name="followupRequestAllocationSelect"
          className={classes.allocationSelect}
        >
          {allocationListApiClassname?.map((allocation: any) => (
            <MenuItem
              value={allocation.id}
              key={allocation.id}
              className={classes.SelectItem}
            >
              {`${groupLookUp[allocation.group_id]?.name} (PI ${
                allocation.pi
              })`}
            </MenuItem>
          ))}
        </Select>
      </div>
      <div data-testid="instrumentlog-request-form">
        <div>
          <Form
            schema={InstrumentLogSelectionFormSchema as any}
            validator={validator}
            onSubmit={handleSubmit as any}
            customValidate={validate}
            disabled={isSubmitting}
            liveValidate
          />
        </div>
        {isSubmitting && (
          <div className={classes.marginTop}>
            <CircularProgress />
          </div>
        )}
      </div>
    </div>
  );
};

export default InstrumentLogForm;

import { useGetGroupsQuery } from "../../ducks/groups";
import { useEffect, useState } from "react";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";
import { useSubmitDefaultFollowupRequestMutation } from "../../ducks/default_followup_requests";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
} from "../../ducks/instruments";
import GroupShareSelect from "../group/GroupShareSelect";

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
  Select: {
    width: "100%",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const NewDefaultFollowupRequest = () => {
  const { classes } = useStyles();

  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const [submitDefaultFollowupRequest] =
    useSubmitDefaultFollowupRequestMutation();

  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);

  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();

  const filteredAllocationListApiClassname = allocationListApiClassname.filter(
    (allocation: any) =>
      allocation.instrument_id in instrumentFormParams &&
      instrumentFormParams[allocation.instrument_id].formSchema !== null &&
      instrumentFormParams[allocation.instrument_id].formSchema !== undefined &&
      allocation.types.includes("triggered"),
  );

  useEffect(() => {
    if (!selectedAllocationId) {
      setSelectedAllocationId(filteredAllocationListApiClassname[0]?.["id"]);
      setSelectedGroupIds([
        filteredAllocationListApiClassname[0]?.["group_id"],
      ]);
    }
  }, [allocationListApiClassname, instrumentFormParams]);

  // need to check both of these conditions as selectedAllocationId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if allocationListApiClassname is not
  // empty.
  if (
    filteredAllocationListApiClassname.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <h3>No allocations with an API class...</h3>;
  }

  if (
    !allGroups ||
    allGroups.length === 0 ||
    telescopeList.length === 0 ||
    instrumentList.length === 0
  ) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const groupLookUp: Record<string, any> = {};

  allGroups?.forEach((group: any) => {
    groupLookUp[group.id] = group;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const allocationLookUp: Record<string, any> = {};

  filteredAllocationListApiClassname?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp: Record<string, any> = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedAllocationChange = (e: any) => {
    setSelectedAllocationId(e.target.value);
  };

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const { default_followup_name, source_filter } = formData;
    delete formData.default_followup_name;
    delete formData.source_filter;
    const json = {
      allocation_id: selectedAllocationId,
      target_group_ids: selectedGroupIds,
      payload: formData,
      default_followup_name,
      source_filter,
    };
    try {
      await submitDefaultFollowupRequest(json).unwrap();
    } catch {
      // notification handled by baseQuery
    }
  };

  const instrumentFormParam =
    instrumentFormParams[allocationLookUp[selectedAllocationId].instrument_id];
  if (!instrumentFormParam) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const { formSchema, uiSchema } = instrumentFormParam;

  // make a copy for both
  const formSchemaCopy = JSON.parse(JSON.stringify(formSchema));

  formSchemaCopy.properties.default_followup_name = {
    default: "DEFAULT-PLAN-NAME",
    type: "string",
  };
  formSchemaCopy.properties.source_filter = {
    title: "Source filter data (i.e. {'classification': 'microlensing'})",
    type: "string",
  };

  const keys_to_remove = ["start_date", "end_date", "queue_name"];
  keys_to_remove.forEach((key) => {
    if (Object.keys(formSchemaCopy.properties).includes(key)) {
      delete formSchemaCopy.properties[key];
    }
    if (
      formSchemaCopy.required?.length > 0 &&
      formSchemaCopy.required.includes(key)
    ) {
      formSchemaCopy.required.splice(formSchemaCopy.required.indexOf(key), 1);
    }
  });

  return (
    <div className={classes.container}>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleSelectedAllocationChange}
        name="followupRequestAllocationSelect"
        className={classes.Select}
      >
        {filteredAllocationListApiClassname?.map((allocation: any) => (
          <MenuItem
            value={allocation.id}
            key={allocation.id}
            className={(classes as any).SelectItem}
          >
            {`${
              telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
            } / ${instLookUp[allocation.instrument_id].name} - ${
              groupLookUp[allocation.group_id].name
            } (PI ${allocation.pi})`}
          </MenuItem>
        ))}
      </Select>
      <br />
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <div data-testid="followup-request-form">
        <div>
          <Form
            schema={formSchemaCopy as any}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit as any}
          />
        </div>
      </div>
    </div>
  );
};

export default NewDefaultFollowupRequest;

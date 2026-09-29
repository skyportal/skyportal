import { useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { useGetGroupsQuery } from "../../ducks/groups";
import { useSubmitDefaultFollowupRequestMutation } from "../../ducks/default_followup_requests";
import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
} from "../../ducks/instruments";
import GroupShareSelect from "../group/GroupShareSelect";
import { localeSafeFields } from "./LocaleSafeNumberField";

const REMOVED_KEYS = ["start_date", "end_date", "queue_name"];

const NewDefaultFollowupRequest = () => {
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const allGroups = useGetGroupsQuery().data?.all;
  const [submitDefaultFollowupRequest] =
    useSubmitDefaultFollowupRequestMutation();
  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[] | null>(null);

  const allocations = allocationListApiClassname.filter(
    (allocation: any) =>
      instrumentFormParams[allocation.instrument_id]?.formSchema != null &&
      allocation.types.includes("triggered"),
  );
  const allocation =
    allocations.find(({ id }: any) => id === selectedAllocationId) ??
    allocations[0];

  if (!allocation) return <h3>No allocations with an API class...</h3>;
  if (!allGroups?.length || !telescopeList.length || !instrumentList.length) {
    return <CircularProgress color="secondary" />;
  }

  const groupIds = selectedGroupIds ?? [allocations[0]?.group_id];

  const handleSubmit = ({ formData }: { formData?: any }) => {
    const { default_followup_name, source_filter, ...payload } = formData;
    submitDefaultFollowupRequest({
      allocation_id: allocation.id,
      target_group_ids: groupIds,
      payload,
      default_followup_name,
      source_filter,
    });
  };

  const { formSchema, uiSchema } =
    instrumentFormParams[allocation.instrument_id];
  const schema = structuredClone(formSchema);
  schema.properties.default_followup_name = {
    default: "DEFAULT-PLAN-NAME",
    type: "string",
  };
  schema.properties.source_filter = {
    title: "Source filter data (i.e. {'classification': 'microlensing'})",
    type: "string",
  };
  REMOVED_KEYS.forEach((key) => delete schema.properties[key]);
  schema.required = schema.required?.filter(
    (key: string) => !REMOVED_KEYS.includes(key),
  );

  const instrumentLabel = (instrumentId: number) => {
    const instrument = instrumentList.find(({ id }) => id === instrumentId);
    const telescope = telescopeList.find(
      ({ id }: any) => id === instrument?.telescope_id,
    );
    return `${telescope?.name} / ${instrument?.name}`;
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Box>
        <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="allocationSelectLabel"
          value={allocation.id}
          onChange={(e) => setSelectedAllocationId(e.target.value)}
          name="followupRequestAllocationSelect"
          fullWidth
        >
          {allocations.map((option: any) => (
            <MenuItem value={option.id} key={option.id}>
              {`${instrumentLabel(option.instrument_id)} - ${
                allGroups.find(({ id }) => id === option.group_id)?.name
              } (PI ${option.pi})`}
            </MenuItem>
          ))}
        </Select>
      </Box>
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={groupIds}
      />
      <Form
        schema={schema}
        validator={validator}
        uiSchema={uiSchema}
        fields={localeSafeFields}
        onSubmit={handleSubmit}
      />
    </Box>
  );
};

export default NewDefaultFollowupRequest;

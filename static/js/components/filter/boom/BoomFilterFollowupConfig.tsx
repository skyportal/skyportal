import { useEffect, useState } from "react";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { makeStyles } from "tss-react/mui";

import {
  useSubmitDefaultFollowupRequestMutation,
  useDeleteDefaultFollowupRequestMutation,
} from "../../../ducks/default_followup_requests";
import { useGetAllocationsApiClassnameQuery } from "../../../ducks/allocations";
import { useGetTelescopesQuery } from "../../../ducks/telescopes";
import {
  useGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
} from "../../../ducks/instruments";
import { useGetGroupsQuery } from "../../../ducks/groups";
import GroupShareSelect from "../../group/GroupShareSelect";
import { localeSafeFields } from "../../followup_request/LocaleSafeNumberField";

const useStyles = makeStyles()(() => ({
  container: { width: "99%", marginTop: "0.5rem" },
  Select: { width: "100%" },
}));

// The constraint / scheduling knobs skyportal's DefaultFollowupRequest accepts
// beyond the instrument payload — injected into the rjsf schema so they render
// with the payload, then split back out on submit. Mirrors Kowalski auto_followup.
const CONSTRAINT_PROPERTIES: Record<string, any> = {
  priority_order: {
    type: "string",
    enum: ["asc", "desc"],
    default: "asc",
    title: "Priority order (asc = higher number wins)",
  },
  validity_days: { type: "integer", default: 7, title: "Validity (days)" },
  not_if_tns_reported: {
    type: "number",
    title: "Skip if TNS-reported within (hours)",
  },
  radius: { type: "number", default: 2, title: "Dedup radius (arcsec)" },
  not_if_duplicates: {
    type: "boolean",
    default: true,
    title: "Skip if a duplicate request exists",
  },
  not_if_classified: { type: "boolean", title: "Skip if classified" },
  not_if_spectra_exist: { type: "boolean", title: "Skip if spectra exist" },
  not_if_tns_classified: { type: "boolean", title: "Skip if TNS-classified" },
  implements_update: {
    type: "boolean",
    default: true,
    title: "Update an existing request instead of creating a new one",
  },
  comment: { type: "string", title: "Comment posted on trigger" },
};
const CONSTRAINT_KEYS = Object.keys(CONSTRAINT_PROPERTIES);

interface BoomFilterFollowupConfigProps {
  filterId: number;
  groupId: number;
  existingDefaultId?: number | null;
  onLinked: (id: number | null) => void;
}

// Configures a skyportal DefaultFollowupRequest scoped to a BOOM filter's group.
// source_filter matching requires a non-null `name` regex, so we use ".*" (any
// obj) + the filter's group_id: it fires for every source the filter auto-saves.
// There is no update endpoint, so editing = delete the old default + recreate.
const BoomFilterFollowupConfig = ({
  filterId,
  groupId,
  existingDefaultId,
  onLinked,
}: BoomFilterFollowupConfigProps) => {
  const { classes } = useStyles();

  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const allGroups = useGetGroupsQuery().data?.all ?? null;

  const [submitDefaultFollowupRequest] =
    useSubmitDefaultFollowupRequestMutation();
  const [deleteDefaultFollowupRequest] =
    useDeleteDefaultFollowupRequestMutation();

  const [selectedAllocationId, setSelectedAllocationId] = useState<any>(null);
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([groupId]);
  const [busy, setBusy] = useState(false);

  const filteredAllocations = allocationListApiClassname.filter(
    (allocation: any) =>
      allocation.instrument_id in instrumentFormParams &&
      instrumentFormParams[allocation.instrument_id]?.formSchema != null &&
      allocation.types.includes("triggered"),
  );

  useEffect(() => {
    if (!selectedAllocationId && filteredAllocations.length > 0) {
      setSelectedAllocationId(filteredAllocations[0]?.id);
    }
  }, [allocationListApiClassname, instrumentFormParams]);

  if (
    filteredAllocations.length === 0 ||
    !selectedAllocationId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return (
      <Typography variant="caption" color="textSecondary">
        No triggerable allocations with an API class are available.
      </Typography>
    );
  }

  if (!allGroups || telescopeList.length === 0 || instrumentList.length === 0) {
    return <CircularProgress color="secondary" size={20} />;
  }

  const telLookUp: Record<string, any> = {};
  telescopeList.forEach((t: any) => (telLookUp[t.id] = t));
  const instLookUp: Record<string, any> = {};
  instrumentList.forEach((i: any) => (instLookUp[i.id] = i));
  const allocationLookUp: Record<string, any> = {};
  filteredAllocations.forEach((a: any) => (allocationLookUp[a.id] = a));
  const groupLookUp: Record<string, any> = {};
  allGroups.forEach((g: any) => (groupLookUp[g.id] = g));

  const instrumentFormParam =
    instrumentFormParams[allocationLookUp[selectedAllocationId].instrument_id];
  if (!instrumentFormParam) {
    return <CircularProgress color="secondary" size={20} />;
  }
  const { formSchema, uiSchema } = instrumentFormParam;

  const formSchemaCopy = JSON.parse(JSON.stringify(formSchema));
  ["start_date", "end_date", "queue_name"].forEach((key) => {
    delete formSchemaCopy.properties[key];
    if (formSchemaCopy.required?.includes(key)) {
      formSchemaCopy.required.splice(formSchemaCopy.required.indexOf(key), 1);
    }
  });
  Object.assign(formSchemaCopy.properties, CONSTRAINT_PROPERTIES);

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setBusy(true);
    try {
      // Delete-and-recreate: there is no default-followup update endpoint.
      if (existingDefaultId) {
        await deleteDefaultFollowupRequest(existingDefaultId).unwrap();
      }
      const constraints: Record<string, any> = {};
      CONSTRAINT_KEYS.forEach((key) => {
        if (formData[key] !== undefined && formData[key] !== "") {
          constraints[key] = formData[key];
        }
        delete formData[key];
      });
      const json = {
        allocation_id: selectedAllocationId,
        target_group_ids: selectedGroupIds,
        payload: formData,
        default_followup_name: `boom-filter-${filterId}`,
        source_filter: { name: ".*", group_id: groupId },
        ...constraints,
      };
      const res: any = await submitDefaultFollowupRequest(json).unwrap();
      onLinked(res?.data?.id ?? res?.id ?? null);
    } catch {
      // notification handled by baseQuery
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async () => {
    setBusy(true);
    try {
      if (existingDefaultId) {
        await deleteDefaultFollowupRequest(existingDefaultId).unwrap();
      }
      onLinked(null);
    } catch {
      // notification handled by baseQuery
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box className={classes.container}>
      <InputLabel id={`followup-alloc-${filterId}`}>Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId={`followup-alloc-${filterId}`}
        value={selectedAllocationId}
        onChange={(e) => setSelectedAllocationId(e.target.value)}
        className={classes.Select}
      >
        {filteredAllocations.map((allocation: any) => (
          <MenuItem value={allocation.id} key={allocation.id}>
            {`${
              telLookUp[instLookUp[allocation.instrument_id].telescope_id].name
            } / ${instLookUp[allocation.instrument_id].name} - ${
              groupLookUp[allocation.group_id]?.name
            } (PI ${allocation.pi})`}
          </MenuItem>
        ))}
      </Select>
      <GroupShareSelect
        groupList={allGroups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <Form
        schema={formSchemaCopy as any}
        validator={validator}
        uiSchema={uiSchema}
        fields={localeSafeFields}
        disabled={busy}
        onSubmit={handleSubmit as any}
      />
      {existingDefaultId ? (
        <Button
          size="small"
          color="error"
          onClick={handleRemove}
          disabled={busy}
          sx={{ mt: 1 }}
        >
          Remove auto-followup
        </Button>
      ) : null}
    </Box>
  );
};

export default BoomFilterFollowupConfig;

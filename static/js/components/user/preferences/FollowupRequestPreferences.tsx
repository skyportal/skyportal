import { useGetGroupsQuery } from "../../../ducks/groups";
import { useEffect, useState } from "react";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";

import { useGetTelescopesQuery } from "../../../ducks/telescopes";
import { useGetAllocationsApiClassnameQuery } from "../../../ducks/allocations";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import {
  useGetInstrumentFormsQuery,
  useGetInstrumentsQuery,
} from "../../../ducks/instruments";

const FollowupRequestPreferences = () => {
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationListApiClassname = [] } =
    useGetAllocationsApiClassnameQuery();
  const allGroups = useGetGroupsQuery().data?.all ?? null;
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const { data: profile } = useGetProfileQuery();
  const defaultAllocationId = profile?.preferences?.["followupDefault"];
  // set the default allocation to be -1 if nothing is in the user preferences
  const [selectedAllocationId, setSelectedAllocationId] = useState(
    defaultAllocationId || -1,
  );

  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  useEffect(() => {
    if (defaultAllocationId) {
      setSelectedAllocationId(defaultAllocationId);
    } else {
      setSelectedAllocationId(-1);
    }
  }, [defaultAllocationId]);

  const allocationListApiClassnameOptions = [
    { id: -1, name: "No preference" },
    ...allocationListApiClassname,
  ];
  const handleChange = (event: any) => {
    const prefs = {
      followupDefault: event.target.value === -1 ? null : event.target.value,
    };
    setSelectedAllocationId(event.target.value);
    updateUserPreferences(prefs);
  };

  if (
    allocationListApiClassname.length === 0 ||
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return (
      <Typography variant="body2" color="textSecondary">
        No allocation with an API yet.
      </Typography>
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

  allocationListApiClassnameOptions?.forEach((allocation: any) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp: Record<string, any> = {};

  instrumentList?.forEach((instrumentObj: any) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  if (Object.keys(instLookUp).length === 0) {
    return (
      <Typography variant="body2" color="textSecondary">
        Loading instruments...
      </Typography>
    );
  }

  return (
    <FormControl fullWidth>
      <InputLabel id="allocationSelectLabel">Allocation</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        label="Allocation"
        value={selectedAllocationId}
        onChange={handleChange}
        name="followupRequestAllocationSelect"
      >
        {allocationListApiClassnameOptions?.map(
          (allocation: any) =>
            (instLookUp[allocation.instrument_id]?.telescope_id ||
              allocation.id === -1) && (
              <MenuItem
                value={allocation.id}
                key={allocation.id}
                sx={{ whiteSpace: "break-spaces" }}
              >
                {allocation.id === -1
                  ? allocation.name
                  : `${
                      telLookUp[
                        instLookUp[allocation.instrument_id]?.telescope_id
                      ]?.name
                    } / ${instLookUp[allocation.instrument_id]?.name} - ${
                      groupLookUp[allocation.group_id]?.name
                    } (PI ${allocation.pi})`}
              </MenuItem>
            ),
        )}
      </Select>
    </FormControl>
  );
};

export default FollowupRequestPreferences;

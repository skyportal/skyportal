import React, { useEffect, useState } from "react";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { makeStyles } from "tss-react/mui";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import * as allocationActions from "../../../ducks/allocations";
import * as profileActions from "../../../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const useStyles = makeStyles()(() => ({
  allocationSelect: {
    width: "40%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
}));

const FollowupRequestPreferences = () => {
  const { telescopeList } = useAppSelector((state) => state.telescopes);
  const { allocationListApiClassname } = useAppSelector(
    (state) => state.allocations,
  );
  const allGroups = useAppSelector((state) => state.groups.all);
  const { instrumentList, instrumentFormParams } = useAppSelector(
    (state) => state.instruments,
  );
  const defaultAllocationId = useAppSelector(
    (state) => state.profile.preferences?.followupDefault,
  );
  // set the default allocation to be -1 if nothing is in the user preferences
  const [selectedAllocationId, setSelectedAllocationId] = useState(
    defaultAllocationId || -1,
  );

  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(allocationActions.fetchAllocationsApiClassname());
  }, [dispatch]);

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
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  if (
    allocationListApiClassname.length === 0 ||
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <h3>No allocations with an API...</h3>;
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

  return (
    <div style={{ marginBottom: "1rem" }}>
      <UserPreferencesHeader
        title="Followup Allocation Preferences"
        popupText="The allocation to display first for followup requests"
      />
      {/* show the select if the instLookUp  isn't empty (has keys) */}
      {Object.keys(instLookUp).length > 0 ? (
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="allocationSelectLabel"
          value={selectedAllocationId}
          onChange={handleChange}
          name="followupRequestAllocationSelect"
          className={classes.allocationSelect}
        >
          {allocationListApiClassnameOptions?.map(
            (allocation: any) =>
              (instLookUp[allocation.instrument_id]?.telescope_id ||
                allocation.id === -1) && (
                <MenuItem
                  value={allocation.id}
                  key={allocation.id}
                  className={classes.SelectItem}
                >
                  {allocation.id === -1 ? (
                    allocation.name
                  ) : (
                    <div>
                      {`${
                        telLookUp[
                          instLookUp[allocation.instrument_id]?.telescope_id
                        ]?.name
                      } / ${instLookUp[allocation.instrument_id]?.name} - ${
                        groupLookUp[allocation.group_id]?.name
                      } (PI ${allocation.pi})`}
                    </div>
                  )}
                </MenuItem>
              ),
          )}
        </Select>
      ) : (
        <div>
          <h3>Loading instrument list...</h3>
        </div>
      )}
    </div>
  );
};

export default FollowupRequestPreferences;

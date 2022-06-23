import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import makeStyles from "@mui/styles/makeStyles";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

const useStyles = makeStyles(() => ({
  allocationSelect: {
    width: "40%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
}));

const FollowupRequestPreferences = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { allocationList } = useSelector((state) => state.allocations);
  const allGroups = useSelector((state) => state.groups.all);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const defaultAllocationId = useSelector(
    (state) => state.profile.preferences.followupDefault
  );
  const [selectedAllocationId, setSelectedAllocationId] =
    useState(defaultAllocationId);

  const classes = useStyles();
  const dispatch = useDispatch();

  useEffect(() => {
    allocationList.unshift({ id: -1, name: "Clear selection" });
  }, [dispatch, allocationList]);

  const handleChange = (event) => {
    const prefs = {
      followupDefault: event.target.value === -1 ? null : event.target.value,
    };
    setSelectedAllocationId(event.target.value);
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  if (
    allocationList.length === 0 ||
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
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

  const allocationLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  allocationList?.forEach((allocation) => {
    allocationLookUp[allocation.id] = allocation;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  return (
    <div style={{ marginBottom: "1rem" }}>
      <UserPreferencesHeader
        title="Followup Allocation Preferences"
        popupText="The allocation to display first for followup requests"
      />
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="allocationSelectLabel"
        value={selectedAllocationId}
        onChange={handleChange}
        name="followupRequestAllocationSelect"
        className={classes.allocationSelect}
      >
        {allocationList?.map((allocation) => (
          <MenuItem
            value={allocation.id}
            key={allocation.id}
            className={classes.SelectItem}
          >
            {allocation.id === -1 ? (
              <div>No preference</div>
            ) : (
              <div>
                {`${
                  telLookUp[instLookUp[allocation.instrument_id].telescope_id]
                    ?.name
                } / ${instLookUp[allocation.instrument_id]?.name} - ${
                  groupLookUp[allocation.group_id]?.name
                } (PI ${allocation.pi})`}
              </div>
            )}
          </MenuItem>
        ))}
      </Select>
    </div>
  );
};

export default FollowupRequestPreferences;

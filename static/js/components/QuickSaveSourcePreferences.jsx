import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { makeStyles } from "@mui/styles";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import UserPreferencesHeader from "./user/UserPreferencesHeader";

import * as profileActions from "../ducks/profile";

const useStyles = makeStyles(() => ({
  allocationSelect: {
    width: "100%",
  },
  SelectItem: {
    display: "flex",
    justifyContent: "space-between",
  },
}));

const QuickSaveSourcePreferences = () => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible,
  );
  const profile = useSelector((state) => state.profile);

  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  useEffect(() => {
    setSelectedGroupIds(profile?.preferences?.quicksave_group_ids || []);
  }, [profile, userAccessibleGroups]);

  const onSubmitGroupIds = (event) => {
    const groupIds = event.target.value;
    setSelectedGroupIds(groupIds);
    const prefs = {
      quicksave_group_ids: groupIds,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div className="quick-save-source-preferences">
      <UserPreferencesHeader
        title="Quick Save Source Preferences"
        popupText="Select the groups you would like to be able to quick save sources to. If any groups are selected, a quick save button will appear on the source page."
      />
      {!userAccessibleGroups && <div>Loading...</div>}
      {userAccessibleGroups && userAccessibleGroups?.length === 0 && (
        <div>
          You do not seem to have access to any groups. Please contact an
          administrator or group admin to be added to a group.
        </div>
      )}
      {userAccessibleGroups && userAccessibleGroups?.length > 0 && (
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="quicksaveGroupsSelectLabel"
          value={selectedGroupIds}
          onChange={onSubmitGroupIds}
          name="quicksaveGroupsSelect"
          className={classes.allocationSelect}
          multiple
        >
          {(userAccessibleGroups || []).map((ignore_group) => (
            <MenuItem
              value={ignore_group.id}
              key={ignore_group.id}
              className={classes.SelectItem}
            >
              {ignore_group.name}
            </MenuItem>
          ))}
        </Select>
      )}
    </div>
  );
};

export default QuickSaveSourcePreferences;

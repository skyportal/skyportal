import { useGetGroupsQuery } from "../../../ducks/groups";
import { useEffect, useMemo, useState } from "react";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const QuickSaveSourcePreferences = () => {
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  const { data: groupsData } = useGetGroupsQuery();
  const userAccessibleGroups = useMemo(
    () => groupsData?.userAccessible ?? [],
    [groupsData],
  );
  const { data: profile } = useGetProfileQuery();

  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  useEffect(() => {
    setSelectedGroupIds(
      (profile?.preferences as any)?.quicksave_group_ids || [],
    );
  }, [profile, userAccessibleGroups]);

  const onSubmitGroupIds = (event: any) => {
    const groupIds = event.target.value;
    setSelectedGroupIds(groupIds);
    const prefs = {
      quicksave_group_ids: groupIds,
    };
    updateUserPreferences(prefs);
  };

  if (!groupsData) return null;

  if (userAccessibleGroups.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        You do not have access to any group yet. Ask an administrator or a group
        admin to add you to one.
      </Typography>
    );
  }

  return (
    <FormControl fullWidth>
      <InputLabel id="quicksaveGroupsSelectLabel">Groups</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="quicksaveGroupsSelectLabel"
        label="Groups"
        value={selectedGroupIds}
        onChange={onSubmitGroupIds}
        name="quicksaveGroupsSelect"
        multiple
      >
        {userAccessibleGroups.map((group) => (
          <MenuItem value={group.id} key={group.id}>
            {group.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default QuickSaveSourcePreferences;

import { useTheme } from "@mui/material/styles";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";

import { Group } from "../../types";
import RemovableChip from "../RemovableChip";

const getStyles = (groupID: number, groupIDs: number[] = [], theme: any) => ({
  fontWeight:
    groupIDs.indexOf(groupID) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

interface GroupShareSelectProps {
  groupList: Group[];
  groupIDs: number[];
  setGroupIDs: (...args: any[]) => void;
  maxGroups?: number;
}

const GroupShareSelect = ({
  groupList,
  groupIDs,
  setGroupIDs,
  maxGroups = 2,
}: GroupShareSelectProps) => {
  const theme = useTheme();
  const groupIDToName: Record<number, string> = {};
  groupList?.forEach(
    (group) => (groupIDToName[group.id] = group.nickname || group.name),
  );

  return (
    <FormControl size="small" sx={{ minWidth: 170, mt: 1 }}>
      <InputLabel id="select-groups-label">Share Data With</InputLabel>
      <Select
        labelId="select-groups-label"
        id="selectGroups"
        MenuProps={{ disableScrollLock: true }}
        multiple
        value={groupIDs as any}
        onChange={(e) => setGroupIDs(e.target.value)}
        label="Share Data With"
        renderValue={(selected: number[]) => {
          if (selected.length <= maxGroups) {
            return (
              <Box sx={{ display: "flex", gap: 0.5 }}>
                {selected.map((value) => (
                  <RemovableChip
                    key={value}
                    size="small"
                    label={groupIDToName[value]}
                    onDelete={() =>
                      setGroupIDs(selected.filter((id) => id !== value))
                    }
                  />
                ))}
              </Box>
            );
          }
          return <Chip size="small" label={`${selected.length} groups`} />;
        }}
      >
        {groupList?.map((group) => (
          <MenuItem
            key={group.id}
            value={group.id}
            style={getStyles(group.id, groupIDs, theme)}
          >
            <div data-testid={`group_${group.id}`}>{group.name}</div>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default GroupShareSelect;

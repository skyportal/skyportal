import React from "react";
import PropTypes from "prop-types";
import { useTheme } from "@mui/material/styles";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import Chip from "@mui/material/Chip";
import Input from "@mui/material/Input";

const getStyles = (groupID, groupIDs = [], theme) => ({
  fontWeight:
    groupIDs.indexOf(groupID) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const GroupShareSelect = ({
  groupList,
  groupIDs,
  setGroupIDs,
  maxGroups = 3,
}) => {
  const theme = useTheme();
  const groupIDToName = {};
  groupList?.forEach(
    (group) => (groupIDToName[group.id] = group.nickname || group.name),
  );

  return (
    <FormControl sx={{ minWidth: 170, mt: 1 }}>
      <InputLabel id="select-groups-label">Share Data With</InputLabel>
      <Select
        labelId="select-groups-label"
        id="selectGroups"
        MenuProps={{ disableScrollLock: true }}
        multiple
        value={groupIDs}
        onChange={(e) => setGroupIDs(e.target.value)}
        input={<Input id="selectGroupsChip" />}
        renderValue={(selected) => {
          if (selected.length <= maxGroups) {
            return selected?.map((value) => (
              <Chip key={value} label={groupIDToName[value]} />
            ));
          }
          return <Chip label={`${selected.length} groups`} />;
        }}
      >
        {groupList?.map((group) => (
          <MenuItem
            key={group.id}
            value={group.id}
            style={getStyles(group.name, groupIDs, theme)}
          >
            <div data-testid={`group_${group.id}`}>{group.name}</div>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

GroupShareSelect.propTypes = {
  groupList: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
  ).isRequired,
  groupIDs: PropTypes.arrayOf(PropTypes.number).isRequired,
  setGroupIDs: PropTypes.func.isRequired,
  maxGroups: PropTypes.number,
};

GroupShareSelect.defaultProps = {
  maxGroups: 2,
};

export default GroupShareSelect;

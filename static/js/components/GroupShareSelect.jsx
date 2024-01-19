import React from "react";
import PropTypes from "prop-types";
import { useTheme } from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import Chip from "@mui/material/Chip";
import Input from "@mui/material/Input";

const useStyles = makeStyles((theme) => ({
  formControl: {
    marginTop: theme.spacing(1),
    minWidth: 150,
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

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
  const classes = useStyles();
  const theme = useTheme();

  const handleChange = (event) => {
    setGroupIDs(event.target.value);
  };

  const groupIDToName = {};
  groupList?.forEach((group) => {
    groupIDToName[group.id] = group.nickname ? group.nickname : group.name;
  });

  return (
    <FormControl className={classes.formControl}>
      <InputLabel id="select-groups-label">Share Data With</InputLabel>
      <Select
        labelId="select-groups-label"
        id="selectGroups"
        MenuProps={{ disableScrollLock: true }}
        multiple
        value={groupIDs}
        onChange={handleChange}
        input={<Input id="selectGroupsChip" />}
        renderValue={(selected) => {
          const numSelected = selected.length;
          if (numSelected <= maxGroups) {
            return (
              <div className={classes.chips}>
                {selected?.map((value) => (
                  <Chip
                    key={value}
                    label={groupIDToName[value]}
                    className={classes.chip}
                  />
                ))}
              </div>
            );
          }
          return (
            <div className={classes.chips}>
              <Chip
                key="chip_groups_summary"
                label={`${numSelected} groups`}
                className={classes.chip}
              />
            </div>
          );
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

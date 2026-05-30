import React from "react";
import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import Chip from "@mui/material/Chip";
import Input from "@mui/material/Input";

import { Group } from "../../types";

const useStyles = makeStyles()((theme) => ({
  formControl: {
    marginTop: theme.spacing(1),
    minWidth: 170,
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

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
  const { classes } = useStyles();
  const theme = useTheme();

  const handleChange = (event: any) => {
    setGroupIDs(event.target.value);
  };

  const groupIDToName: Record<number, string> = {};
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
        value={groupIDs as any}
        onChange={handleChange}
        input={<Input id="selectGroupsChip" />}
        renderValue={
          ((selected: number[]) => {
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
          }) as any
        }
      >
        {groupList?.map((group) => (
          <MenuItem
            key={group.id}
            value={group.id}
            style={getStyles(group.name as any, groupIDs, theme)}
          >
            <div data-testid={`group_${group.id}`}>{group.name}</div>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default GroupShareSelect;

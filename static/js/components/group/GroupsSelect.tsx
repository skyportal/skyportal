import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import { makeStyles } from "tss-react/mui";
import { useTheme } from "@mui/material/styles";

import { useAppSelector } from "../../types/hooks";
import { Group } from "../../types";

const useStyles = makeStyles()(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
    maxWidth: "20rem",
  },
  groupsMenu: {
    minWidth: "12rem",
  },
}));

const getStyles = (group: Group, selectedGroups: Group[], theme: any) => ({
  fontWeight:
    selectedGroups.indexOf(group) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

interface GroupsSelectProps {
  selectedGroups: Group[];
  setSelectedGroups: (...args: any[]) => void;
}

const GroupsSelect = (props: GroupsSelectProps) => {
  const { selectedGroups, setSelectedGroups } = props;

  const { classes } = useStyles();
  const theme = useTheme();
  const groups = useAppSelector((state) => state.groups.userAccessible);

  const ITEM_HEIGHT = 48;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5,
        width: 250,
      },
    },
  };

  return (
    <>
      {groups?.length > 0 && (
        <div>
          <FormControl className={classes.groupsMenu}>
            <InputLabel id="groups-input-label">Groups</InputLabel>
            <Select
              labelId="groups-input-label"
              label="Groups"
              id="groups-select"
              multiple
              value={selectedGroups}
              onChange={(event) => {
                setSelectedGroups(event.target.value);
              }}
              input={<Input id="groups-select" />}
              renderValue={(selected: Group[]) => (
                <div className={classes.chips}>
                  {selected?.map((group) =>
                    selected.indexOf(group) === 0 ? (
                      <Chip key={group.id} label={group.name} />
                    ) : (
                      selected.indexOf(group) === 1 && (
                        <Chip
                          key="more_groups"
                          label={`+${selected?.length - 1}`}
                        />
                      )
                    ),
                  )}
                </div>
              )}
              MenuProps={MenuProps}
            >
              {groups?.map((group) => (
                <MenuItem
                  key={group.id}
                  value={group as any}
                  style={getStyles(group, selectedGroups, theme)}
                >
                  {group.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </div>
      )}
    </>
  );
};

export default GroupsSelect;

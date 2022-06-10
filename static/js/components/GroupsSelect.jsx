import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import Input from "@material-ui/core/Input";
import InputLabel from "@material-ui/core/InputLabel";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import Chip from "@material-ui/core/Chip";
import FormControl from "@material-ui/core/FormControl";
import { makeStyles, useTheme } from "@material-ui/core/styles";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
    maxWidth: "20rem",
  },
  groupsMenu: {
    minWidth: "12rem",
  },
}));

const getStyles = (group, selectedGroups, theme) => ({
  fontWeight:
    selectedGroups.indexOf(group) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const GroupsSelect = (props) => {
  const { selectedGroups, setSelectedGroups } = props;

  const classes = useStyles();
  const theme = useTheme();
  const groups = useSelector((state) => state.groups.userAccessible);

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
              labelId="groups-select-label"
              id="groups-select"
              multiple
              value={selectedGroups}
              onChange={(event) => {
                setSelectedGroups(event.target.value);
              }}
              input={<Input id="groups-select" />}
              renderValue={(selected) => (
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
                    )
                  )}
                </div>
              )}
              MenuProps={MenuProps}
            >
              {groups?.map((group) => (
                <MenuItem
                  key={group.id}
                  value={group}
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

GroupsSelect.propTypes = {
  selectedGroups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
    })
  ).isRequired,
  setSelectedGroups: PropTypes.func.isRequired,
};

export default GroupsSelect;

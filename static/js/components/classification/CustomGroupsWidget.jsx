import { useSelector } from "react-redux";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import Input from "@mui/material/Input";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import React from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

const CustomGroupsWidget = ({ value, onChange, options }) => {
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.userAccessible);

  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

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
      <InputLabel id="classificationGroupSelectLabel">
        Choose Group (all groups if blank)
      </InputLabel>
      <Select
        id="groupSelect"
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        input={<Input id="selectGroupsChip" />}
        labelId="classificationGroupSelectLabel"
        value={value || ""}
        renderValue={(selected) => (
          <div className={classes.chips}>
            {selected?.map((group) => (
              <Chip
                key={group}
                label={groupIDToName[group]}
                className={classes.chip}
              />
            ))}
          </div>
        )}
        MenuProps={MenuProps}
        fullWidth
        multiple
      >
        {options.enumOptions.length > 0 &&
          options.enumOptions?.map((group) => (
            <MenuItem
              value={group.value}
              key={group.value.toString()}
              data-testid={`notificationGroupSelect_${group.value}`}
            >
              {group.label}
            </MenuItem>
          ))}
      </Select>
    </>
  );
};

CustomGroupsWidget.propTypes = {
  value: PropTypes.arrayOf(PropTypes.string).isRequired,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.shape({
    enumOptions: PropTypes.arrayOf(PropTypes.shape({})),
  }).isRequired,
};

export default CustomGroupsWidget;

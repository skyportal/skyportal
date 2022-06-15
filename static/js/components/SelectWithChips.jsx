import React, { useState } from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  useTheme,
  Chip,
} from "@mui/material";

const useStyles = makeStyles((theme) => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
    maxWidth: "25rem",
  },
  formControl: {
    minWidth: "12rem",
    paddingRight: theme.spacing(1),
  },
}));

const getStyles = (option, opts, theme) => ({
  fontWeight:
    opts.indexOf(option) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const SelectWithChips = (props) => {
  const classes = useStyles();
  const theme = useTheme();
  const [opts, setOpts] = useState([]);
  const { label, id, initValue, onChange, options } = props;

  const max_chars = 90;
  // find the max number of chips we want to display. To do that, find the index of the selected element after which we are over the max number of chars
  let char_count = 0;
  let max_chip_nb = -1;
  for (let i = 0; i < initValue.length; i += 1) {
    if (!initValue[i]) {
      break;
    } else {
      char_count += initValue[i].length;
    }
    if (char_count > max_chars) {
      max_chip_nb = i;
      break;
    }
  }

  if (max_chip_nb === -1 && char_count > 0 && char_count <= max_chars) {
    max_chip_nb = initValue.length;
  }

  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: "20rem",
      },
    },
  };

  return (
    <>
      <FormControl key={`${id}${label}`} className={classes.formControl}>
        <InputLabel key={`${id}${label}`}>{label}</InputLabel>
        <Select
          id={id}
          multiple
          value={initValue || []}
          onChange={(event) => {
            onChange(event);
            setOpts(
              event.target.value.includes("Clear selections")
                ? []
                : event.target.value
            );
          }}
          renderValue={(selected) => (
            <div className={classes.chips}>
              {selected.map((value) =>
                selected.indexOf(value) < max_chip_nb ? (
                  <Chip key={value} label={value} />
                ) : (
                  selected.indexOf(value) === max_chip_nb && (
                    <Chip
                      key={value}
                      label={`+${selected?.length - max_chip_nb}`}
                    />
                  )
                )
              )}
            </div>
          )}
          MenuProps={MenuProps}
        >
          {options?.map((option) => (
            <MenuItem
              key={option}
              value={option}
              style={getStyles(option, opts, theme)}
            >
              {option}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </>
  );
};

SelectWithChips.propTypes = {
  label: PropTypes.string.isRequired,
  id: PropTypes.string.isRequired,
  initValue: PropTypes.arrayOf(PropTypes.string),
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(PropTypes.string).isRequired,
};

SelectWithChips.defaultProps = {
  initValue: [],
};

export default SelectWithChips;

import React, { useState } from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import { useTheme } from "@mui/material/styles";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  formControl: {
    minWidth: "12rem",
    width: "100%",
  },
}));

const getStyles = (option, opts, theme) => ({
  fontWeight:
    opts.indexOf(option) === -1
      ? theme.typography.fontWeightRegular
      : theme.typography.fontWeightMedium,
});

const menuProps = { PaperProps: { style: { maxHeight: "20rem" } } };

const SelectWithChips = (props) => {
  const classes = useStyles();
  const theme = useTheme();
  const [opts, setOpts] = useState([]);
  const { label, id, initValue, onChange, options } = props;
  const MAX_CHAR = 90;
  const cumSum = [];

  initValue?.forEach((item, index) => {
    cumSum.push(item?.length + (index > 0 ? cumSum[index - 1] : 0));
  });

  const max_chips_nb =
    initValue?.length > 0 && !initValue.some((word) => word === undefined)
      ? cumSum.filter((sum) => sum <= MAX_CHAR).length
      : -1;

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        multiple
        value={initValue || []}
        onChange={(event) => {
          onChange(event);
          setOpts(
            event.target.value.includes("Clear selections")
              ? []
              : event.target.value,
          );
        }}
        renderValue={(selected) => (
          <div className={classes.chips}>
            {selected.slice(0, max_chips_nb).map((value) => (
              <Chip key={value} label={value} />
            ))}
            {selected.length > max_chips_nb && (
              <Chip label={`+${selected.length - max_chips_nb}`} />
            )}
          </div>
        )}
        MenuProps={menuProps}
      >
        {options?.map((option, index) => (
          <MenuItem
            key={index}
            value={option}
            style={getStyles(option, opts, theme)}
          >
            {option}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
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

const SelectLabelWithChips = (props) => {
  // the difference with SelectWithChips is that the initValue is not a list of strings, but a list of element with an id and a label
  const classes = useStyles();
  const theme = useTheme();
  const [opts, setOpts] = useState([]);
  const { label, id, initValue, onChange, options } = props;
  const MAX_CHAR = 90;
  const cumSum = [];
  const labels = initValue?.map((item) => item.label);

  labels?.forEach((item, index) => {
    cumSum.push(item?.length + (index > 0 ? cumSum[index - 1] : 0));
  });

  const max_chips_nb =
    labels?.length > 0 && !labels.some((word) => word === undefined)
      ? cumSum.filter((sum) => sum <= MAX_CHAR).length
      : -1;

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        multiple
        label={label}
        value={initValue || []}
        onChange={(event) => {
          onChange(event);
          setOpts(
            event.target.value.includes("Clear selections")
              ? []
              : event.target.value,
          );
        }}
        renderValue={(selected) => (
          <div className={classes.chips}>
            {selected.slice(0, max_chips_nb).map((value) => (
              <Chip key={value.id} label={value.label} />
            ))}
            {selected.length > max_chips_nb && (
              <Chip label={`+${selected.length - max_chips_nb}`} />
            )}
          </div>
        )}
        MenuProps={menuProps}
      >
        {options?.map((option) => (
          <MenuItem
            key={option.id}
            value={option}
            style={getStyles(option, opts, theme)}
          >
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

SelectLabelWithChips.propTypes = {
  label: PropTypes.string.isRequired,
  id: PropTypes.string.isRequired,
  initValue: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    }),
  ),
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      label: PropTypes.string.isRequired,
    }),
  ).isRequired,
};

SelectLabelWithChips.defaultProps = {
  initValue: [],
};

const SelectSingleLabelWithChips = (props) => {
  // the difference with SelectWithChips is that the initValue is not a list of strings, but a list of element with an id and a label
  const classes = useStyles();
  const theme = useTheme();
  const opts = [];
  const { label, id, initValue, onChange, options } = props;

  return (
    <FormControl className={classes.formControl}>
      <InputLabel>{label}</InputLabel>
      <Select
        id={id}
        label={label}
        value={initValue || ""}
        onChange={(event) => onChange(event)}
        renderValue={(selected) => <Chip label={selected.label} />}
        MenuProps={menuProps}
      >
        {options?.map((option) => (
          <MenuItem
            key={option.id}
            value={option}
            style={getStyles(option, opts, theme)}
          >
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

SelectSingleLabelWithChips.propTypes = {
  label: PropTypes.string.isRequired,
  id: PropTypes.string.isRequired,
  initValue: PropTypes.shape({
    id: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
  }),
  onChange: PropTypes.func.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      label: PropTypes.string.isRequired,
    }),
  ).isRequired,
};

SelectSingleLabelWithChips.defaultProps = {
  initValue: {},
};

export default SelectWithChips;

export { SelectLabelWithChips, SelectSingleLabelWithChips };

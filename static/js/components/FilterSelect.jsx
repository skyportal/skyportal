import React from "react";
import { Controller, useForm } from "react-hook-form";
import { useSelector } from "react-redux";
import { makeStyles } from "@material-ui/core/styles";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Chip from "@material-ui/core/Chip";

const useStyles = makeStyles((theme) => ({
  formControl: {
    minWidth: "12rem",
    paddingRight: theme.spacing(1),
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
}));

const FilterSelect = ({ onFilterSelectChange, initValue, parent }) => {
  const classes = useStyles();
  let filtersEnums = [];
  filtersEnums = filtersEnums.concat(
    useSelector((state) => state.enum_types.enum_types.ALLOWED_BANDPASSES)
  );
  filtersEnums.sort();
  filtersEnums.unshift("Clear selections");

  const { control } = useForm();

  const ITEM_HEIGHT = 48;
  const ITEM_PADDING_TOP = 8;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
        width: 250,
      },
    },
  };

  return (
    <Controller
      name="filterSelect"
      control={control}
      render={({ onChange }) => (
        <FormControl className={classes.formControl}>
          <InputLabel id="select-photometry-plot-filter-label">
            Filters
          </InputLabel>
          <Select
            id={`filterSelect${parent}`}
            multiple
            value={initValue || []}
            label="Select photometry filter"
            onChange={(event) => {
              onChange(event.target.value);
              onFilterSelectChange(event);
            }}
            renderValue={(selected) => (
              <div>
                {selected.map((value) => (
                  <Chip key={value} label={value} />
                ))}
              </div>
            )}
            MenuProps={MenuProps}
          >
            {filtersEnums.map((filter) => (
              <MenuItem key={filter} value={filter}>
                <div data-testid={`filter_${filter}`}>{filter}</div>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
    />
  );
};

export default FilterSelect;

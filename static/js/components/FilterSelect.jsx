import React from 'react';
import { Controller } from 'react-hook-form';
import { useSelector, useDispatch } from "react-redux";
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

const FilterSelect = ({ control }) => {
  const classes = useStyles()
  let filters = ["Clear selections"];
  const filters_enums = useSelector(
    (state) => state.enum_types.enum_types.ALLOWED_BANDPASSES
  );

  if (filters_enums && filters.length === 1) {
    filters = filters.concat(filters_enums);
  }
  
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
      render={({onChange, value}) => (
        <FormControl className={classes.formControl}>
          <InputLabel id="select-photometry-plot-filter-label">
            Filters
          </InputLabel>
          <Select
            labelId="demo-simple-select-helper-label"
            id="demo-simple-select-helper"
            multiple
            value={value || []}
            label="Select photometry filter"
            onChange={(event) => {
              onChange(event.target.value)
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
            {filters.map((filter) => (
              <MenuItem key={filter} value={filter}>
                <div data-testid={`filter_${filter}`}>{filter}</div>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      />
  )
}

export default FilterSelect;
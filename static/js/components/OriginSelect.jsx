import React from "react";
import { Controller, useForm } from "react-hook-form";
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

const OriginSelect = ({ onOriginSelectChange, initValue, parent }) => {
  const classes = useStyles();
  const origins = ["Clear selections", "Muphoten", "STDpipe"];

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
  const { control } = useForm();

  return (
    <Controller
      name="originSelect"
      control={control}
      render={({ onChange }) => (
        <FormControl className={classes.formControl}>
          <InputLabel id="select-origin-label">Origin</InputLabel>
          <Select
            labelId="select-origin-label"
            id={`originSelect${parent}`}
            multiple
            value={initValue || []}
            label="Select origin"
            onChange={(event) => {
              onChange(event.target.value);
              onOriginSelectChange(event);
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
            {origins.map((origin) => (
              <MenuItem key={origin} value={origin}>
                <div data-testid={`origin_${origin}`}>{origin}</div>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
    />
  );
};

export default OriginSelect;

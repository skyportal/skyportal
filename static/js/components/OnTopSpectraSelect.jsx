import React from "react";
import PropTypes from "prop-types";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";

const useStyles = makeStyles(() => ({
  form: {
    minWidth: "12rem",
  },
}));

const OnTopSpectraSelect = (props) => {
  const { spectra, onTopSpectraId, setOnTopSpectraId } = props;
  const classes = useStyles();

  return (
    <FormControl className={classes.form}>
      <InputLabel id="demo-simple-select-helper-label">
        Select on top spectra
      </InputLabel>
      <Select
        labelId="demo-simple-select-helper-label"
        id="demo-simple-select-helper"
        value={onTopSpectraId}
        label="Select on top spectra"
        onChange={(event) => setOnTopSpectraId(event.target.value)}
      >
        {spectra?.map((spec) => (
          <MenuItem key={spec.id} value={spec.id}>
            {spec.instrument_name} ({dayjs(spec.observed_at).format("MM/DD/YY")}
            )
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

OnTopSpectraSelect.propTypes = {
  spectra: PropTypes.arrayOf(
    PropTypes.shape({
      instrument_name: PropTypes.string,
      id: PropTypes.number,
      observed_at: PropTypes.string,
    })
  ).isRequired,
  onTopSpectraId: PropTypes.string.isRequired,
  setOnTopSpectraId: PropTypes.func.isRequired,
};

export default OnTopSpectraSelect;

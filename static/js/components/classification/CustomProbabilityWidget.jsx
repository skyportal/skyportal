// Custom form widget for probability because rxjs MUI UpdownWidget does not have working min/max/step
// https://github.com/rjsf-team/react-jsonschema-form/issues/2022
import TextField from "@mui/material/TextField";
import React from "react";
import PropTypes from "prop-types";

const CustomProbabilityWidget = ({ value, onChange }) => (
  <TextField
    id="probability"
    label="Probability"
    type="number"
    helperText="[0-1]"
    InputLabelProps={{
      shrink: true,
    }}
    inputProps={{
      min: "0",
      max: "1",
      step: "0.0001",
    }}
    value={value || ""}
    onChange={(event) => {
      onChange(event.target.value);
    }}
  />
);

CustomProbabilityWidget.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
};
CustomProbabilityWidget.defaultProps = {
  value: "",
};

export default CustomProbabilityWidget;

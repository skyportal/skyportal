import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import React from "react";
import PropTypes from "prop-types";

// Custom form widget for the classifications to format and display the contexts as well
const CustomClassificationWidget = ({ value, onChange, options }) => {
  const filteringOptions = createFilterOptions({
    matchFrom: "start",
    stringify: (option) => option,
  });
  return (
    <Autocomplete
      id="classification"
      filterOptions={filteringOptions}
      options={options.enumOptions?.map((option) => option.value)}
      onChange={(event, newValue) => {
        onChange(newValue);
      }}
      value={value || ""}
      renderOption={(props, option) => {
        const [classification, context] = option.split(" <> ");
        return (
          <div {...props}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                margin: "0.5rem",
                marginTop: "0.25rem",
                justifyContent: "center",
                alignItems: "left",
              }}
              id={classification}
            >
              <b>{classification}</b>
              {context !== "" && <br />}
              {context}
            </div>
          </div>
        );
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label="Classification"
          variant="outlined"
          required
        />
      )}
    />
  );
};

CustomClassificationWidget.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  options: PropTypes.shape({
    enumOptions: PropTypes.arrayOf(PropTypes.shape({})),
  }).isRequired,
};

CustomClassificationWidget.defaultProps = {
  value: "",
};

export default CustomClassificationWidget;

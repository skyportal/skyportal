// NewDropDownSearchBar.jsx
import React from "react";
import PropTypes from "prop-types";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

const NewDropDownSearchBar = ({
  optionsList,
  selectedOption,
  onOptionChange,
  searchValue,
  onSearchChange,
  label,
}) => (
  <Autocomplete
    options={optionsList}
    getOptionLabel={(option) => `${option.telescopeName} / ${option.name}`}
    value={selectedOption}
    onChange={onOptionChange}
    renderInput={(params) => (
      <TextField
        {...params}
        label={label}
        variant="outlined"
        onChange={(e) => onSearchChange(e.target.value)}
        value={searchValue}
      />
    )}
  />
);

NewDropDownSearchBar.propTypes = {
  optionsList: PropTypes.arrayOf(
    PropTypes.shape({
      telescopeName: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      // Add other properties as needed
    })
  ).isRequired,
  selectedOption: PropTypes.shape({
    id: PropTypes.number.isRequired,
    // Add other properties as needed
  }),
  onOptionChange: PropTypes.func.isRequired,
  searchValue: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
  label: PropTypes.string.isRequired,
};

NewDropDownSearchBar.defaultProps = {
  selectedOption: null, // Provide a default value for selectedOption
};

export default NewDropDownSearchBar;

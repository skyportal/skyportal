// NewDropDownsearchBar.jsx
import React from "react";
import PropTypes from "prop-types"; // Import PropTypes for prop validation
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";

const NewDropDownSearchBar = ({
  instrumentList,
  selectedInstrument,
  onInstrumentChange,
  searchValue,
  onSearchChange,
}) => (
  <Autocomplete
    options={instrumentList}
    getOptionLabel={(instrument) =>
      `${instrument.telescopeName} / ${instrument.name}`
    }
    value={selectedInstrument}
    onChange={onInstrumentChange}
    renderInput={(params) => (
      <TextField
        {...params}
        label="Select an instrument"
        variant="outlined"
        onChange={(e) => onSearchChange(e.target.value)}
        value={searchValue}
      />
    )}
  />
);

// Define prop types for the InstrumentSearchBar component
NewDropDownSearchBar.propTypes = {
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      telescopeName: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      // Add other properties as needed
    })
  ).isRequired,
  selectedInstrument: PropTypes.shape({
    id: PropTypes.number.isRequired,
    // Add other properties as needed
  }),
  onInstrumentChange: PropTypes.func.isRequired,
  searchValue: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
};

NewDropDownSearchBar.defaultProps = {
  selectedInstrument: null,
};

export default NewDropDownSearchBar;

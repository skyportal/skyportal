import React from "react";
import PropTypes from "prop-types";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
// eslint-disable-next-line import/no-unresolved

const InstrumentSearchBar = ({
  instrumentList,
  selectedInstrument,
  onInstrumentChange,
  searchValue,
  onSearchChange,
}) => {
  return (
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
};

InstrumentSearchBar.propTypes = {
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      telescopeName: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
    })
  ).isRequired,
  selectedInstrument: PropTypes.shape({
    id: PropTypes.number.isRequired,
  }),
  onInstrumentChange: PropTypes.func.isRequired,
  searchValue: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
};

InstrumentSearchBar.defaultProps = {
  selectedInstrument: null,
};

export default InstrumentSearchBar;

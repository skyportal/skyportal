import React from "react";
import PropTypes from "prop-types";
import SelectWithChips from "./SelectWithChips";

const OriginSelect = ({ onOriginSelectChange, initValue, parent }) => {
  const origins = ["Clear selections", "Muphoten", "STDpipe"];

  return (
    <SelectWithChips
      label="Origin"
      id={`originSelect${parent}`}
      initValue={initValue}
      onChange={onOriginSelectChange}
      options={origins}
    />
  );
};

OriginSelect.propTypes = {
  onOriginSelectChange: PropTypes.func.isRequired,
  initValue: PropTypes.arrayOf(PropTypes.string),
  parent: PropTypes.string.isRequired,
};

OriginSelect.defaultProps = {
  initValue: [],
};

export default OriginSelect;

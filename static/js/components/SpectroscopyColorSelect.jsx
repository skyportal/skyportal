import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import SelectWithChips from "./SelectWithChips";

const SpectroscopyColorSelect = ({
  onColorSelectChange,
  initValue,
  parent,
}) => {
  const colorPalette = useSelector((state) => state.config.colorPalette);

  return (
    <SelectWithChips
      label="Color"
      id={`colorSelect${parent}`}
      onChange={onColorSelectChange}
      options={colorPalette}
      initValue={initValue}
    />
  );
};

SpectroscopyColorSelect.propTypes = {
  onColorSelectChange: PropTypes.func.isRequired,
  initValue: PropTypes.arrayOf(PropTypes.string),
  parent: PropTypes.string.isRequired,
};

SpectroscopyColorSelect.defaultProps = {
  initValue: [],
};

export default SpectroscopyColorSelect;

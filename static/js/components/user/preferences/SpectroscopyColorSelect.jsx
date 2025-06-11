import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";

import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";

const SpectroscopyColorSelect = ({ onColorSelectChange, initValue }) => {
  const colorPalette = useSelector((state) => state.config.colorPalette);

  return (
    <div style={{ width: "100%" }}>
      <InputLabel>Color</InputLabel>
      <Select fullWidth value={initValue} onChange={onColorSelectChange}>
        {(colorPalette || []).map((color) => (
          <MenuItem key={color} value={color}>
            <div style={{ width: "1rem", height: "1rem", background: color }} />
          </MenuItem>
        ))}
      </Select>
    </div>
  );
};

SpectroscopyColorSelect.propTypes = {
  onColorSelectChange: PropTypes.func.isRequired,
  initValue: PropTypes.arrayOf(PropTypes.string),
};

SpectroscopyColorSelect.defaultProps = {
  initValue: [],
};

export default SpectroscopyColorSelect;

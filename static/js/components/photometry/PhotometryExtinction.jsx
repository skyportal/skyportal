import React from "react";
import PropTypes from "prop-types";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

const PhotometryExtinction = ({ showExtinction, setShowExtinction }) => {
  return (
    <div>
      <FormControlLabel
        control={
          <Switch
            checked={showExtinction}
            onChange={(e) => setShowExtinction(e.target.checked)}
            size="small"
            data-testid="photometry_extinction_toggle"
          />
        }
        label="Extinction"
      />
    </div>
  );
};

PhotometryExtinction.propTypes = {
  showExtinction: PropTypes.bool.isRequired,
  setShowExtinction: PropTypes.func.isRequired,
};

export default PhotometryExtinction;

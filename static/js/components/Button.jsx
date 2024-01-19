import React from "react";
import PropTypes from "prop-types";
import MuiButton from "@mui/material/Button";
import LoadingButton from "@mui/lab/LoadingButton";

const Button = ({ primary, secondary, async, ...muiButtonProps }) => {
  if (muiButtonProps.startIcon) {
    throw new Error(
      "Error: startIcon used in Button props. Please use endIcon as specified in the SkyPortal style documentation: https://skyportal.io/docs/styling.html#buttons",
    );
  }
  if (async) {
    return (
      <LoadingButton
        loadingIndicator="Loading..."
        variant="contained"
        color="primary"
        // eslint-disable-next-line react/jsx-props-no-spreading
        {...muiButtonProps}
      />
    );
  }
  if (primary || secondary) {
    return (
      <MuiButton
        variant="contained"
        color={primary ? "primary" : "grey"}
        // eslint-disable-next-line react/jsx-props-no-spreading
        {...muiButtonProps}
      />
    );
  }
  // eslint-disable-next-line react/jsx-props-no-spreading
  return <MuiButton {...muiButtonProps} />;
};

Button.propTypes = {
  primary: PropTypes.bool,
  secondary: PropTypes.bool,
  async: PropTypes.bool,
};

Button.defaultProps = {
  primary: false,
  secondary: false,
  async: false,
};

export default Button;

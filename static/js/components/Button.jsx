import React, { forwardRef } from "react";
import PropTypes from "prop-types";
import MuiButton from "@mui/material/Button";
import LoadingButton from "@mui/lab/LoadingButton";

const Button = forwardRef(
  ({ primary, secondary, loading, ...muiButtonProps }, ref) => {
    if (muiButtonProps.startIcon) {
      throw new Error(
        "Error: startIcon used in Button props. Please use endIcon as specified in the SkyPortal style documentation: https://skyportal.io/docs/styling.html#buttons",
      );
    }
    if (loading) {
      return (
        <LoadingButton
          ref={ref}
          loadingIndicator=" Loading... "
          variant="contained"
          color="primary"
          loading
          {...muiButtonProps}
        />
      );
    }
    if (primary || secondary) {
      return (
        <MuiButton
          ref={ref}
          variant="contained"
          color={primary ? "primary" : "grey"}
          {...muiButtonProps}
        />
      );
    }
    return <MuiButton ref={ref} {...muiButtonProps} />;
  },
);

Button.displayName = "Button";

Button.propTypes = {
  primary: PropTypes.bool,
  secondary: PropTypes.bool,
  loading: PropTypes.bool,
};

Button.defaultProps = {
  primary: false,
  secondary: false,
  async: false,
};

export default Button;

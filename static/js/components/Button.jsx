import React, { forwardRef } from "react";
import PropTypes from "prop-types";
import MuiButton from "@mui/material/Button";

const Button = forwardRef(
  ({ primary, secondary, loading, ...muiButtonProps }, ref) => {
    if (muiButtonProps.startIcon) {
      throw new Error(
        "Error: startIcon used in Button props. Please use endIcon as specified in the SkyPortal style documentation: https://skyportal.io/docs/styling.html#buttons",
      );
    }
    const commonProps = {
      ref,
      ...muiButtonProps,
    };

    if (loading) {
      return (
        <MuiButton
          ref={ref}
          size={commonProps?.size}
          variant={commonProps?.variant}
          disabled
        >
          Loading...
        </MuiButton>
      );
    }

    if (primary || secondary) {
      commonProps.color = primary ? "primary" : "secondary";
      commonProps.variant = commonProps?.variant || "contained";

      if (secondary && commonProps.variant === "outlined") {
        commonProps.sx = {
          ...commonProps?.sx,
          borderColor: "secondary.dark",
          color: "secondary.contrastText",
        };
      }
    }

    return <MuiButton {...commonProps} />;
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
  loading: false,
};

export default Button;

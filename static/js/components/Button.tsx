import React, { forwardRef } from "react";
import MuiButton from "@mui/material/Button";
import LoadingButton from "@mui/lab/LoadingButton";

interface ButtonProps {
  primary?: boolean;
  secondary?: boolean;
  async?: boolean;
  [key: string]: any;
}

const Button = forwardRef<any, ButtonProps>(
  (
    { primary = false, secondary = false, async = false, ...muiButtonProps },
    ref,
  ) => {
    if (muiButtonProps.startIcon) {
      throw new Error(
        "Error: startIcon used in Button props. Please use endIcon as specified in the SkyPortal style documentation: https://skyportal.io/docs/styling.html#buttons",
      );
    }
    if (async) {
      return (
        <LoadingButton
          ref={ref}
          loadingIndicator="Loading..."
          variant="contained"
          color="primary"
          {...muiButtonProps}
        />
      );
    }
    if (primary || secondary) {
      return (
        <MuiButton
          ref={ref}
          variant="contained"
          color={(primary ? "primary" : "grey") as any}
          {...muiButtonProps}
        />
      );
    }
    return <MuiButton ref={ref} {...muiButtonProps} />;
  },
);

Button.displayName = "Button";

export default Button;

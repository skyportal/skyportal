import React, { forwardRef } from "react";
import { Link as RouterLink } from "react-router-dom";
import PropTypes from "prop-types";
import MuiLink from "@mui/material/Link";

const Link = forwardRef(
  ({ primary, secondary, notBold, ...muiLinkProps }, ref) => {
    const commonProps = {
      ref,
      ...muiLinkProps,
      color: primary ? "primary.main" : muiLinkProps.color || "secondary.dark",
      ...(!notBold && { fontWeight: "bold" }),
    };

    return <MuiLink {...commonProps} component={RouterLink} />;
  },
);

Link.displayName = "Link";

Link.propTypes = {
  primary: PropTypes.bool,
  secondary: PropTypes.bool,
  notBold: PropTypes.bool,
};

Link.defaultProps = {
  primary: false,
  secondary: false,
  notBold: false,
};

export default Link;

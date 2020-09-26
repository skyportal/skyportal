import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import { createMuiTheme, ThemeProvider } from "@material-ui/core/styles";
import CssBaseline from "@material-ui/core/CssBaseline";

const Theme = ({ disableTransitions, children }) => {
  const theme = useSelector((state) => state.profile.preferences.theme);
  const materialTheme = createMuiTheme({
    palette: {
      type: theme || "light",
      background:
        theme === "dark" ? { default: "#303030" } : { default: "#f0f2f5" },
    },
    // Only added during testing; removes animations, transitions, and
    // rippple effects
    ...(disableTransitions && {
      props: {
        MuiButtonBase: {
          disableRipple: true,
        },
      },
      overrides: {
        MuiCssBaseline: {
          "@global": {
            "*, *::before, *::after": {
              transition: "none !important",
              animation: "none !important",
            },
          },
        },
      },
    }),
  });

  return (
    <ThemeProvider theme={materialTheme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
};

Theme.propTypes = {
  disableTransitions: PropTypes.bool,
  children: PropTypes.node.isRequired,
};

Theme.defaultProps = {
  disableTransitions: false,
};

export default Theme;

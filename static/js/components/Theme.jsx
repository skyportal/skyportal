import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
} from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

const Theme = ({ disableTransitions, children }) => {
  const theme = useSelector((state) => state.profile.preferences.theme);
  const darkMode = theme === "dark";
  const materialTheme = createTheme({
    palette: {
      mode: theme || "light",
      primary: {
        main: "rgb(69, 123, 157)",
        light: "rgb(106, 149, 176)",
        dark: "rgb(29, 53, 87)",
        contrastText: "#ffffff",
      },
      secondary: {
        main: "rgb(220, 220, 220)",
        light: "rgb(230, 230, 230)",
        dark: "rgb(160, 160, 160)",
        contrastText: "rgba(0, 0, 0, 0.65)",
      },
      background: darkMode
        ? { default: "#1e1e1e", paper: "#191919" }
        : { default: "#f0f2f5", paper: "#f0f2f5" },
    },
    typography: {
      h1: {
        fontSize: "2.2rem",
        fontWeight: "400",
      },
    },
    plotFontSizes: {
      titleFontSize: 15,
      labelFontSize: 15,
    },
    components: {
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
      },
      MuiCssBaseline: {
        styleOverrides: {
          ".rbc-current-time-indicator": {
            backgroundColor: "#87ea12 !important",
            height: "2px !important",
          },
          ".MuiMenuItem-root[data-value='']": {
            color: "grey",
          },
        },
      },
    },
    // Only added during testing; removes animations, transitions, and ripple effects
    ...(disableTransitions && {
      components: {
        defaultProps: {
          MuiButtonBase: {
            disableRipple: true,
          },
        },
        MuiCssBaseline: {
          styleOverrides: {
            "@global": {
              "*, *::before, *::after": {
                transition: "none !important",
                animation: "none !important",
              },
            },
          },
        },
      },
    }),
  });

  return (
    <StyledEngineProvider injectFirst>
      <ThemeProvider theme={materialTheme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </StyledEngineProvider>
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

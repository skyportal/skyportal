import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import { createTheme, ThemeProvider } from "@material-ui/core/styles";
import CssBaseline from "@material-ui/core/CssBaseline";
import grey from "@material-ui/core/colors/grey";

const Theme = ({ disableTransitions, children }) => {
  const theme = useSelector((state) => state.profile.preferences.theme);
  const dark = theme === "dark";
  const materialTheme = createTheme({
    // Color palette inspired from: https://coolors.co/e63946-f1faee-a8dadc-457b9d-1d3557
    palette: {
      type: theme || "light",
      primary: {
        main: "#457b9d",
        light: "#457b9d",
        dark: "#1d3557",
        contrastText: "#fff",
      },
      secondary: {
        main: "#b1dae9",
        light: "#b1dae9",
        dark: "#76aace",
        contrastText: "#fff",
      },
      info: {
        main: "#f1faee",
      },
      warning: {
        main: "#fca311",
      },
      error: {
        main: "#e63946",
      },
      background: dark ? { default: "#303030" } : { default: "#f0f2f5" },
    },
    overrides: {
      MuiTypography: {
        body1: {
          color: dark ? grey[50] : null,
        },
      },
      MuiButton: {
        textPrimary: {
          color: dark ? "#b1dae9" : null,
        },
        outlinedPrimary: {
          color: dark ? "#b1dae9" : null,
        },
      },
      MuiCssBaseline: {
        "@global": {
          html: {
            fontFamily: "Roboto, Helvetica, Arial, sans-serif",

            /* Scrollbar styling */

            /* Works on Firefox */
            scrollbarWidth: "thin",
            scrollbarColor: dark
              ? `${grey[700]} ${grey[800]}`
              : `${grey[400]} ${grey[100]}`,
            overflowY: "auto",

            /* Works on Chrome, Edge, and Safari */
            "& *::-webkit-scrollbar": {
              width: "12px",
            },

            "& *::-webkit-scrollbar-track": {
              background: dark ? grey[800] : grey[100],
            },

            "& *::-webkit-scrollbar-thumb": {
              backgroundColor: dark ? grey[700] : grey[400],
              borderRadius: "20px",
              border: dark
                ? `3px solid ${grey[800]}`
                : `3px solid ${grey[100]}`,
            },
          },
        },
      },
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

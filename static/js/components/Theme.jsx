import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
} from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { grey } from "@mui/material/colors";

const Theme = ({ disableTransitions, children }) => {
  const theme = useSelector((state) => state.profile.preferences.theme);
  const dark = theme === "dark";

  const greyTheme = createTheme({
    palette: {
      grey: {
        main: grey[300],
        dark: grey[400],
      },
    },
  });
  const materialTheme = createTheme(greyTheme, {
    palette: {
      mode: theme || "light",
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
      background: dark
        ? { default: "#303030", paper: "#808080" }
        : { default: "#f0f2f5", paper: "#f0f2f5" },
    },
    plotFontSizes: {
      titleFontSize: 15,
      labelFontSize: 15,
    },
    components: {
      MuiTypography: {
        styleOverrides: {
          body1: {
            color: dark ? grey[50] : null,
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        variants: [
          {
            props: { variant: "contained", color: "grey" },
            style: {
              color: greyTheme.palette.getContrastText(
                greyTheme.palette.grey[300],
              ),
            },
          },
        ],
        styleOverrides: {
          textPrimary: {
            color: dark ? "#b1dae9" : null,
          },
          outlinedPrimary: {
            color: dark ? "#b1dae9" : null,
          },
        },
      },
      MuiCssBaseline: {
        styleOverrides: {
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
    },

    // Only added during testing; removes animations, transitions, and
    // rippple effects
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

import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
} from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { grey } from "@mui/material/colors";

const Theme = ({ disableTransitions, children }) => {
  const theme = useSelector((state) => state.profile.preferences.theme);
  const dark = theme === "dark";

  const greyTheme = createTheme({
    palette: {
      grey: {
        main: grey[500],
        dark: grey[200],
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
        dark: "#b3bbbb",
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
        ? { default: "rgba(23,23,23,0.96)", paper: "#343434" }
        : { default: "#e7e7e7", paper: "#e7e6e6" },
    },
    plotFontSizes: {
      titleFontSize: 15,
      labelFontSize: 15,
    },
    components: {
      MuiTypography: {
        styleOverrides: {
          body1: {
            color: dark ? grey[100] : null,
          },
          body2: {
            color: dark ? grey[50] : null,
          },
          subtitle1: {
            color: dark ? grey[50] : null,
          },
          subtitle2: {
            color: dark ? grey[50] : null,
          },
          button: {
            color: dark ? grey[50] : null,
          },
          caption: {
            color: dark ? grey[50] : null,
          },
          overline: {
            color: dark ? grey[50] : null,
          },
          h1: {
            color: dark ? grey[50] : null,
          },
          h2: {
            color: dark ? grey[50] : null,
          },
          h3: {
            color: dark ? grey[50] : null,
          },
          h4: {
            color: dark ? grey[50] : null,
          },
          h5: {
            color: dark ? grey[50] : null,
          },
          h6: {
            color: dark ? grey[50] : null,
          },
        },
      },
      MuiButton: {
        variants: [
          {
            props: { variant: "contained", color: "white" },
            style: {
              color: greyTheme.palette.getContrastText(
                greyTheme.palette.grey[200]
              ),
            },
          },
        ],
        styleOverrides: {
          textPrimary: {
            color: dark ? "#a4a4a4" : null,
          },
          outlinedPrimary: {
            color: dark ? "#d2e4ea" : null,
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

import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import { createMuiTheme, ThemeProvider } from "@material-ui/core/styles";
import CssBaseline from "@material-ui/core/CssBaseline";

const Theme = ({ disableTransitions, children }) => {
  const theme = useSelector((state) => state.profile.preferences.theme);
  const materialTheme = createMuiTheme({
    // Custom colors. These are from: https://coolors.co/e63946-f1faee-a8dadc-457b9d-1d3557
    colors: {
      darkBlue: '#1d3557', // Prussian Blue
      midBlue: '#457b9d', // Celadon Blue
      lightBlue: '#a8dadc', //Powder Blue
      white: '#f1faee', // Honeydew
      red: '#e63946', // Imperial Red
    },
    palette: {
      type: theme || "light",
      primary: {
        main: '#1d3557', // darkBlue
        light: '#4a5e84',
        dark: '#000e2e',
        contrastText: '#fff',
      },
      secondary: {
        main: '#a8dadc', // lightBlue
        light: '#76aace',
        dark: '#a8dadc',
        contrastText: '#fff',
      },
      info: {
        main: '#f1faee', // white
      },
      warning: {
        main: '#fca311',
      },
      error: {
        main: '#e63946', // red
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

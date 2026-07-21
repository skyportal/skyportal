import { useGetProfileQuery } from "../ducks/profile";
import { useActiveTeam } from "../ducks/teams";
import React from "react";

import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
} from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import { grey } from "@mui/material/colors";

interface ThemeProps {
  disableTransitions?: boolean;
  children: React.ReactNode;
}

const Theme = ({ disableTransitions = false, children }: ThemeProps) => {
  const theme = (useGetProfileQuery().data?.preferences as any)?.theme;
  const dark = theme === "dark";

  // When a team is active, its colors drive the whole MUI palette so every
  // primary/secondary-colored element themes at once. No active team → the
  // original SkyPortal palette.
  const { activeTeam } = useActiveTeam();
  const primaryColor = activeTeam?.primary_color || "#457b9d";
  const secondaryColor = activeTeam?.secondary_color || "#b1dae9";

  const greyTheme = createTheme({
    palette: {
      grey: {
        main: grey[300],
        dark: grey[400],
      },
    },
  } as any);
  const materialTheme = createTheme(greyTheme, {
    palette: {
      mode: theme || "light",
      primary: {
        main: primaryColor,
        light: primaryColor,
        dark: "#1d3557",
        contrastText: "#fff",
      },
      secondary: {
        main: secondaryColor,
        light: secondaryColor,
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
  } as any);

  return (
    <StyledEngineProvider injectFirst>
      <ThemeProvider theme={materialTheme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </StyledEngineProvider>
  );
};

export default Theme;

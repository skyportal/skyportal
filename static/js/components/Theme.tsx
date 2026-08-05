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

const THEME_KEY = "skyportal:theme";
const SCHEME_KEY = "skyportal:darkScheme";

interface DarkScheme {
  label: string;
  default: string;
  paper: string;
  error: string;
  text: string;
  textSecondary: string;
  divider: string;
  scrollTrack: string;
  scrollThumb: string;
}

export const DARK_SCHEMES = {
  slate: {
    label: "Blue",
    default: "#0e1726",
    paper: "#16233a",
    error: "#ff6b74",
    text: "#e6edf5",
    textSecondary: "#9fb3c8",
    divider: "rgba(168, 218, 220, 0.16)",
    scrollTrack: "#16233a",
    scrollThumb: "#1e3050",
  },
  graphite: {
    label: "Dark",
    default: "#303030",
    paper: "#424242",
    error: "#ff6b74",
    text: "#fafafa",
    textSecondary: "rgba(255, 255, 255, 0.7)",
    divider: "rgba(255, 255, 255, 0.16)",
    scrollTrack: "#303030",
    scrollThumb: "#4e4e4e",
  },
} satisfies Record<string, DarkScheme>;

export type DarkSchemeName = keyof typeof DARK_SCHEMES;

export const LIGHT_BACKGROUND = "#f0f2f5";

export const DEFAULT_DARK_SCHEME: DarkSchemeName = "slate";

const schemeFor = (name?: string | null): DarkScheme =>
  name && name in DARK_SCHEMES
    ? DARK_SCHEMES[name as DarkSchemeName]
    : DARK_SCHEMES[DEFAULT_DARK_SCHEME];

const Theme = ({ disableTransitions = false, children }: ThemeProps) => {
  const preferences = useGetProfileQuery().data?.preferences as any;
  const profileTheme = preferences?.theme;
  const profileScheme = preferences?.darkScheme;
  const [stored] = React.useState(() => ({
    theme: window.localStorage.getItem(THEME_KEY),
    scheme: window.localStorage.getItem(SCHEME_KEY),
  }));
  const theme = profileTheme ?? stored.theme ?? undefined;
  const dark = theme === "dark";
  const scheme = schemeFor(profileScheme ?? stored.scheme);

  React.useEffect(() => {
    if (!profileTheme) return;
    window.localStorage.setItem(THEME_KEY, profileTheme);
    if (profileScheme) window.localStorage.setItem(SCHEME_KEY, profileScheme);
    document.documentElement.style.backgroundColor =
      profileTheme === "dark" ? schemeFor(profileScheme).default : "";
  }, [profileTheme, profileScheme]);

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
        main: dark ? scheme.error : "#e63946",
      },
      background: dark
        ? { default: scheme.default, paper: scheme.paper }
        : { default: LIGHT_BACKGROUND, paper: LIGHT_BACKGROUND },
      ...(dark && {
        text: { primary: scheme.text, secondary: scheme.textSecondary },
        divider: scheme.divider,
      }),
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
                ? `${scheme.scrollThumb} ${scheme.scrollTrack}`
                : `${grey[400]} ${grey[100]}`,
              overflowY: "auto",

              /* Works on Chrome, Edge, and Safari */
              "& *::-webkit-scrollbar": {
                width: "12px",
              },

              "& *::-webkit-scrollbar-track": {
                background: dark ? scheme.scrollTrack : grey[100],
              },

              "& *::-webkit-scrollbar-thumb": {
                backgroundColor: dark ? scheme.scrollThumb : grey[400],
                borderRadius: "20px",
                border: dark
                  ? `3px solid ${scheme.scrollTrack}`
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

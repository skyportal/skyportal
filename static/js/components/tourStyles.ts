import { alpha, useTheme } from "@mui/material/styles";
import type { Options, PartialDeep, Styles } from "react-joyride";

// Shared look for every Joyride tour (guided tours + feature announcements)
export const useTourStyles = () => {
  const theme = useTheme();
  const dark = theme.palette.mode === "dark";

  const options: Partial<Options> = {
    // Lift above the app's low sidebar z-index (~140) and MUI modals.
    zIndex: 2000,
    skipBeacon: true,
    targetWaitTimeout: 3000,
    showProgress: true,
    width: 380,
    backgroundColor: theme.palette.background.paper,
    arrowColor: theme.palette.background.paper,
    textColor: theme.palette.text.primary,
    primaryColor: theme.palette.primary.main,
    overlayColor: alpha("#0b1220", dark ? 0.72 : 0.48),
    spotlightPadding: 8,
    spotlightRadius: 8,
  };

  const styles: PartialDeep<Styles> = {
    tooltip: {
      borderRadius: "0.75rem",
      padding: "1.25rem",
      border: `1px solid ${theme.palette.divider}`,
      boxShadow: theme.shadows[8],
      fontFamily: theme.typography.fontFamily,
    },
    tooltipContainer: { textAlign: "left" },
    tooltipTitle: {
      // Room for the close button.
      paddingRight: "1.5rem",
      fontSize: "1.05rem",
      fontWeight: 600,
      color: dark ? theme.palette.secondary.main : theme.palette.primary.main,
    },
    tooltipContent: {
      padding: "0.5rem 0 0",
      fontSize: "0.875rem",
      lineHeight: 1.6,
      color: theme.palette.text.secondary,
    },
    tooltipFooter: { marginTop: "1rem", gap: "0.5rem" },
    buttonPrimary: {
      borderRadius: "2rem",
      padding: "0.4rem 1.1rem",
      fontSize: "0.85rem",
      fontWeight: 600,
      color: theme.palette.primary.contrastText,
      boxShadow: `0 0.125rem 0.5rem ${alpha(theme.palette.primary.main, 0.4)}`,
    },
    buttonBack: {
      marginRight: 0,
      fontSize: "0.85rem",
      fontWeight: 500,
      color: theme.palette.text.secondary,
    },
    buttonSkip: {
      fontSize: "0.85rem",
      color: theme.palette.text.secondary,
    },
    buttonClose: {
      top: "0.75rem",
      right: "0.75rem",
      color: theme.palette.text.secondary,
    },
  };

  return { options, styles };
};

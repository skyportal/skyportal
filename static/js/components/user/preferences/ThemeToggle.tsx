import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import { useTheme } from "@mui/material/styles";

import {
  DARK_SCHEMES,
  DEFAULT_DARK_SCHEME,
  LIGHT_BACKGROUND,
} from "../../Theme";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const MODES = [
  { value: "light", label: "White", color: LIGHT_BACKGROUND, text: "#1d1d1d" },
  ...Object.entries(DARK_SCHEMES).map(([value, scheme]) => ({
    value,
    label: scheme.label,
    color: scheme.paper,
    text: scheme.text,
  })),
];

const ThemeToggle = () => {
  const preferences = useGetProfileQuery().data?.preferences as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const theme = useTheme();

  const current =
    preferences?.theme === "dark"
      ? preferences?.darkScheme || DEFAULT_DARK_SCHEME
      : "light";

  const selectMode = (value: string) => () => {
    if (value === current) return;
    updateUserPreferences(
      value === "light"
        ? { theme: "light" }
        : { theme: "dark", darkScheme: value },
    );
  };

  return (
    <Box
      data-testid="theme-toggle"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.75,
        p: 0.5,
        borderRadius: 999,
        border: 1,
        borderColor: "divider",
        backgroundColor: "background.default",
      }}
    >
      {MODES.map(({ value, label, color, text }) => {
        const selected = value === current;
        return (
          <ButtonBase
            key={value}
            onClick={selectMode(value)}
            aria-label={`${label} mode`}
            data-testid={`theme-${value}`}
            sx={{
              height: "2.25rem",
              minWidth: "2.25rem",
              px: selected ? 1.5 : 0,
              borderRadius: 999,
              border: 1,
              borderColor: "divider",
              backgroundColor: color,
              color: text,
              fontSize: "0.8125rem",
              fontWeight: "bold",
              whiteSpace: "nowrap",
              transition: theme.transitions.create(
                ["min-width", "padding", "border-color"],
                { duration: theme.transitions.duration.short },
              ),
              "&:hover": { borderColor: "text.secondary" },
            }}
          >
            {selected && label}
          </ButtonBase>
        );
      })}
    </Box>
  );
};

export default ThemeToggle;

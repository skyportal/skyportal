import { useState } from "react";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import MoreVertIcon from "@mui/icons-material/MoreVert";

import {
  DARK_SCHEMES,
  DEFAULT_DARK_SCHEME,
  LIGHT_BACKGROUND,
} from "../../Theme";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

// Each swatch is painted with the background/text of the mode it selects, so
// the group doubles as a preview.
const MODES = [
  { value: "light", label: "White", color: LIGHT_BACKGROUND, text: "#1d1d1d" },
  ...Object.entries(DARK_SCHEMES).map(([value, scheme]) => ({
    value,
    label: scheme.label,
    color: scheme.default,
    text: scheme.text,
  })),
];

const ThemeToggle = () => {
  const preferences = useGetProfileQuery().data?.preferences as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  const current =
    preferences?.theme === "dark"
      ? preferences?.darkScheme || DEFAULT_DARK_SCHEME
      : "light";

  const selectMode = (value: string) => () => {
    setAnchorEl(null);
    if (value === current) return;
    updateUserPreferences(
      value === "light"
        ? { theme: "light" }
        : { theme: "dark", darkScheme: value },
    );
  };

  if (isMobile) {
    return (
      <>
        <IconButton
          onClick={(event) => setAnchorEl(event.currentTarget)}
          aria-label="Choose theme"
          data-testid="theme-toggle-menu"
        >
          <MoreVertIcon />
        </IconButton>
        <Menu
          anchorEl={anchorEl}
          open={!!anchorEl}
          onClose={() => setAnchorEl(null)}
        >
          {MODES.map(({ value, label, color, text }) => (
            <MenuItem
              key={value}
              selected={value === current}
              onClick={selectMode(value)}
              data-testid={`theme-${value}`}
              sx={{
                backgroundColor: color,
                color: text,
                fontWeight: value === current ? "bold" : undefined,
                opacity: value === current ? 1 : 0.45,
                "&.Mui-selected, &:hover, &.Mui-selected:hover": {
                  backgroundColor: color,
                  opacity: 1,
                },
              }}
            >
              {label} mode
            </MenuItem>
          ))}
        </Menu>
      </>
    );
  }

  return (
    <Box sx={{ display: "flex" }} data-testid="theme-toggle">
      {MODES.map(({ value, label, color, text }) => {
        const selected = value === current;
        return (
          <ButtonBase
            key={value}
            onClick={selectMode(value)}
            aria-label={`${label} mode`}
            data-testid={`theme-${value}`}
            sx={{
              width: selected ? "9rem" : "5.5rem",
              height: "2.5rem",
              px: 1,
              borderRadius: 1,
              border: 1,
              borderColor: "divider",
              backgroundColor: color,
              color: text,
              overflow: "hidden",
              whiteSpace: "nowrap",
              fontWeight: "bold",
              opacity: selected ? 1 : 0.6,
              transition: theme.transitions.create(
                ["width", "opacity", "filter"],
                { duration: theme.transitions.duration.short },
              ),
              "&:hover": { opacity: 1, filter: "none" },
            }}
          >
            {selected ? `${label} mode` : label}
          </ButtonBase>
        );
      })}
    </Box>
  );
};

export default ThemeToggle;

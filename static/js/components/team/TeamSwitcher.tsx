/**
 * Header dropdown that sets the active team (a per-user preference). Switching
 * teams re-scopes team-aware widgets (e.g. the News Feed) and re-skins the app
 * banner with the team's color and logo. It is a view control only: it never
 * changes what data the user can access.
 */
import { useEffect } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import type { SelectChangeEvent } from "@mui/material/Select";

import { useUpdateUserPreferencesMutation } from "../../ducks/profile";
import { useActiveTeam, useGetTeamsQuery } from "../../ducks/teams";

const ColorDot = ({ color }: { color?: string | null }) => (
  <span
    style={{
      display: "inline-block",
      width: 10,
      height: 10,
      borderRadius: "50%",
      marginRight: 8,
      flex: "0 0 auto",
      backgroundColor: color || "#9b9a9a",
    }}
  />
);

const TeamSwitcher = () => {
  const { data: teams } = useGetTeamsQuery();
  const { activeTeamId, activeTeam } = useActiveTeam();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  // Re-skin the app for the active team via an injected stylesheet. Using CSS
  // selectors (rather than setting styles on specific nodes) means elements
  // that mount later — the hover-expanded sidebar, the quick-search input —
  // are themed too. The banner and sidebar take the primary color; the search
  // input takes the lighter secondary/accent color.
  useEffect(() => {
    const styleId = "team-theme-style";
    const primary = activeTeam?.primary_color;
    const secondary = activeTeam?.secondary_color;
    const background = activeTeam?.background_url;

    const existing = document.getElementById(styleId);
    if (!primary && !secondary && !background) {
      if (existing) existing.remove();
      return;
    }
    const styleEl =
      (existing as HTMLStyleElement | null) ??
      document.head.appendChild(document.createElement("style"));
    styleEl.id = styleId;

    const rules: string[] = [];
    if (primary) {
      rules.push(
        `header.MuiAppBar-root { background: ${primary} !important; }`,
      );
      rules.push(`.MuiDrawer-paper { background: ${primary} !important; }`);
    }
    if (secondary) {
      // Quick-search widgets: the search input and the "type" (Sources/…)
      // dropdown. Scoped by their stable ids so the team switcher select and
      // other header controls are untouched.
      rules.push(
        `header .MuiAutocomplete-root .MuiOutlinedInput-root,
         header .MuiInputBase-root:has(#type-select) {
           background-color: ${secondary} !important;
         }`,
        `header .MuiInputBase-root:has(#type-select) fieldset,
         header .MuiAutocomplete-root .MuiOutlinedInput-root fieldset {
           border-color: ${secondary} !important;
         }`,
        // Header action icons (refresh, search, notifications bell, notes,
        // menu). IconButtons only, so the team switcher's dropdown arrow and
        // the profile avatar are left alone.
        `header .MuiIconButton-root svg { color: ${secondary} !important; }`,
      );
    }
    if (background) {
      rules.push(`body { background-image: url("${background}") !important; }`);
    }
    styleEl.textContent = rules.join("\n");

    return () => {
      const el = document.getElementById(styleId);
      if (el) el.remove();
    };
  }, [
    activeTeam?.primary_color,
    activeTeam?.secondary_color,
    activeTeam?.background_url,
  ]);

  if (!teams || teams.length === 0) {
    return null;
  }

  const handleChange = (event: SelectChangeEvent) => {
    const value = event.target.value;
    updateUserPreferences({ activeTeam: value === "" ? null : Number(value) });
  };

  return (
    <FormControl size="small" data-testid="teamSwitcher">
      <Select
        value={activeTeamId != null ? String(activeTeamId) : ""}
        onChange={handleChange}
        displayEmpty
        variant="outlined"
        sx={{
          color: "white",
          minWidth: 150,
          ".MuiOutlinedInput-notchedOutline": {
            borderColor: "rgba(255,255,255,0.5)",
          },
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: "white",
          },
          ".MuiSvgIcon-root": { color: "white" },
          ".MuiSelect-select": {
            display: "flex",
            alignItems: "center",
            py: 0.5,
          },
        }}
        renderValue={() => (
          <Box sx={{ display: "flex", alignItems: "center" }}>
            {activeTeam ? (
              <>
                {activeTeam.logo_url ? (
                  <Avatar
                    src={activeTeam.logo_url}
                    alt={activeTeam.name}
                    sx={{ width: 20, height: 20, mr: 1 }}
                  />
                ) : (
                  <ColorDot color={activeTeam.primary_color ?? null} />
                )}
                {activeTeam.name}
              </>
            ) : (
              <>
                <ColorDot color={null} />
                All Teams
              </>
            )}
          </Box>
        )}
      >
        <MenuItem value="">
          <ColorDot color={null} />
          All Teams
        </MenuItem>
        {teams.map((team) => (
          <MenuItem key={team.id} value={String(team.id)}>
            {team.logo_url ? (
              <Avatar
                src={team.logo_url}
                alt={team.name}
                sx={{ width: 20, height: 20, mr: 1 }}
              />
            ) : (
              <ColorDot color={team.primary_color ?? null} />
            )}
            {team.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default TeamSwitcher;

import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useJoyride, EVENTS } from "react-joyride";

import Paper from "@mui/material/Paper";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import CloseIcon from "@mui/icons-material/Close";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetFiltersQuery } from "../../ducks/filter";
import { useFetchSourcesQuery } from "../../ducks/sources";
import { useAppDispatch } from "../../types/hooks";
import store from "../../store";
import { setSidebar } from "../../ducks/sidebar";
import { TOUR_STEPS } from "./GettingStartedTour";

// Onboarding checklist + guided tour, rendered as a Home Page widget. Shows for
// every user until dismissed (persisted in `preferences.onboardingDismissed`)
// and can be reopened at any time. Each checklist step auto-detects completion
// from the user's profile, groups, filters, saved sources, and preferences.
// The `classes` prop is injected by the Home Page grid but unused here.
const GettingStarted = (_props: { classes?: Record<string, string> }) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { data: profile } = useGetProfileQuery();
  const { data: groups } = useGetGroupsQuery();
  const { data: filters } = useGetFiltersQuery();
  // Only need whether this user has saved any source; keep the page tiny.
  const { data: sources } = useFetchSourcesQuery({
    numPerPage: 1,
    savedByCurrentUser: true,
  });
  const [updatePreferences] = useUpdateUserPreferencesMutation();
  const { controls, on, Tour } = useJoyride({
    steps: TOUR_STEPS,
    continuous: true,
    // App sets a low sidebar z-index (~140); lift the tour above it and MUI
    // modals so tooltips aren't hidden behind the drawer.
    options: { zIndex: 2000 },
  });

  // Sidebar-targeted steps need the drawer mounted; on mobile it's a closed
  // temporary drawer, so open it for the tour and restore state afterwards.
  const sidebarWasOpen = useRef(false);
  useEffect(() => {
    const offStart = on(EVENTS.TOUR_START, () => {
      sidebarWasOpen.current = (store.getState() as any).sidebar?.open ?? false;
      dispatch(setSidebar(true));
    });
    const offEnd = on(EVENTS.TOUR_END, () => {
      dispatch(setSidebar(sidebarWasOpen.current));
    });
    return () => {
      offStart();
      offEnd();
    };
  }, [on, dispatch]);

  const dismissed = profile?.preferences?.["onboardingDismissed"] === true;

  const profileDone =
    Boolean(profile?.first_name) && (profile?.affiliations?.length ?? 0) > 0;
  const groupDone = (groups?.user ?? []).some((g: any) => !g.single_user_group);
  const tokenDone = (profile?.tokens?.length ?? 0) > 0;
  const filterDone = ((filters as any[] | undefined)?.length ?? 0) > 0;
  const sourceDone = (sources?.totalMatches ?? 0) > 0;
  const prefs = profile?.preferences ?? {};
  const notificationsDone =
    Object.keys(prefs["notifications"] ?? {}).length > 0;
  const homeCustomizedDone = Boolean(prefs["layouts"]);

  // `tour` names a PAGE_TOURS entry launched as a how-to on the destination.
  const checklist = [
    {
      label: "Complete your profile",
      done: profileDone,
      to: "/profile",
      tour: "profile",
      help: "Add your name and affiliation so collaborators know who you are.",
    },
    {
      label: "Join a group",
      done: groupDone,
      to: "/groups",
      tour: "groups",
      help: "Groups are how data is shared in SkyPortal — join or create one to see and share sources.",
    },
    {
      label: "Set up a candidate filter",
      done: filterDone,
      to: "/groups",
      tour: "groups",
      help: "Open a group and add an alert filter to start collecting candidates.",
    },
    {
      label: "Save your first source",
      done: sourceDone,
      to: "/candidates",
      tour: "candidates",
      help: "Scan the candidates page and save a promising candidate as a source.",
    },
    {
      label: "Create an API token",
      done: tokenDone,
      to: "/profile",
      tour: "profile",
      help: "Generate a token to query SkyPortal programmatically from scripts or notebooks.",
    },
    {
      label: "Set your notifications",
      done: notificationsDone,
      to: "/profile",
      tour: "profile",
      help: "Choose how you want to hear about new sources, classifications, and GCN events.",
    },
    {
      label: "Customize your home page",
      done: homeCustomizedDone,
      to: "/",
      tour: undefined as string | undefined,
      help: "Drag, resize, add, or remove these widgets to make the home page yours.",
    },
  ];

  if (dismissed) {
    // Keep a small affordance so the checklist/tour can be reopened anytime.
    return (
      <Paper data-testid="tour-getting-started" sx={{ p: 2, height: "100%" }}>
        <Typography variant="subtitle1" gutterBottom>
          Getting started
        </Typography>
        <Button
          size="small"
          data-testid="tour-reopen"
          onClick={() => updatePreferences({ onboardingDismissed: false })}
        >
          Show checklist
        </Button>
      </Paper>
    );
  }

  return (
    <Paper
      data-testid="tour-getting-started"
      sx={{ p: 2, height: "100%", overflow: "auto" }}
    >
      {Tour}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography variant="h6">Getting started</Typography>
        <Tooltip title="Dismiss">
          <IconButton
            size="small"
            data-testid="tour-dismiss"
            onClick={() => updatePreferences({ onboardingDismissed: true })}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        Welcome to SkyPortal! Complete these steps to get going.
      </Typography>
      <List dense data-testid="tour-getting-started-checklist">
        {checklist.map((item) => (
          <ListItemButton
            key={item.label}
            onClick={() =>
              navigate(item.to, item.tour ? { state: { tour: item.tour } } : {})
            }
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              {item.done ? (
                <CheckCircleIcon color="success" fontSize="small" />
              ) : (
                <RadioButtonUncheckedIcon color="disabled" fontSize="small" />
              )}
            </ListItemIcon>
            <ListItemText primary={item.label} secondary={item.help} />
          </ListItemButton>
        ))}
      </List>
      <Button
        size="small"
        variant="outlined"
        data-testid="tour-start"
        onClick={() => controls.start()}
      >
        Take the tour
      </Button>
    </Paper>
  );
};

export default GettingStarted;

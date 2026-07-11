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
import TourIcon from "@mui/icons-material/Tour";
import CloseIcon from "@mui/icons-material/Close";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetFiltersQuery } from "../../ducks/filter";
import { useFetchSourcesQuery } from "../../ducks/sources";
import { useGetRecentGcnEventsQuery } from "../../ducks/recentGcnEvents";
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
  const { data: recentGcnEvents } = useGetRecentGcnEventsQuery();
  const [updatePreferences] = useUpdateUserPreferencesMutation();
  const { controls, on, Tour } = useJoyride({
    steps: TOUR_STEPS,
    continuous: true,
    // Scroll each target into view, including the first step.
    scrollToFirstStep: true,
    // App sets a low sidebar z-index (~140); lift the tour above it and MUI
    // modals so tooltips aren't hidden behind the drawer. Show tooltips
    // directly instead of a click-to-open beacon.
    options: { zIndex: 2000, skipBeacon: true },
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

  // Effective ACLs; checklist items tagged with an `acl` are shown only to
  // users who have it (the page tours gate their own steps the same way).
  const permissions: string[] = (profile as any)?.permissions ?? [];
  // The source tour runs on a real source page, so point it at the user's
  // first saved source when they have one.
  const firstSourceId = (sources as any)?.sources?.[0]?.id;
  // The group tour runs on a group page; use the first multi-user group.
  const firstGroupId = (groups?.user ?? []).find(
    (g: any) => !g.single_user_group,
  )?.id;
  // The GCN tour runs on an event page; use the most recent event.
  const firstGcnDateobs = (recentGcnEvents as any)?.[0]?.dateobs;

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
      label: "Explore a source page",
      // Launching a tour isn't a trackable completion, so show no checkbox.
      explore: true,
      to: firstSourceId ? `/source/${firstSourceId}` : "/sources",
      tour: firstSourceId ? "source" : undefined,
      help: "Tour a source: photometry, comments, classifications, sharing, and follow-up.",
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
    {
      label: "Manage your group",
      explore: true,
      to: firstGroupId ? `/group/${firstGroupId}` : "/groups",
      tour: firstGroupId ? "group" : undefined,
      help: "Add members, approve join requests, and attach filters and streams.",
    },
    {
      label: "Explore GCN events",
      explore: true,
      to: firstGcnDateobs ? `/gcn_events/${firstGcnDateobs}` : "/gcn_events",
      tour: firstGcnDateobs ? "gcnevents" : undefined,
      help: "Localizations, counterpart searches, and observation plans for multi-messenger alerts.",
    },
    // Facility-management tours: shown only to users with the relevant ACL.
    // These launch a how-to tour rather than track a completion, so they show
    // no checkbox (there's no per-user signal for who created a telescope/etc.).
    {
      label: "Register a telescope",
      explore: true,
      to: "/telescopes",
      tour: "telescopes",
      acl: "Manage telescopes",
      help: "Add a telescope and its location so you can attach instruments.",
    },
    {
      label: "Register an instrument",
      explore: true,
      to: "/instruments",
      tour: "instruments",
      acl: "Manage instruments",
      help: "Add an instrument and its filter list to a telescope.",
    },
    {
      label: "Set up observing shifts",
      explore: true,
      to: "/shifts",
      tour: "shifts",
      acl: "Manage shifts",
      help: "Coordinate who's on duty for scanning and follow-up.",
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
        {checklist
          .filter(
            (item) =>
              !(item as any).acl || permissions.includes((item as any).acl),
          )
          .map((item) => (
            <ListItemButton
              key={item.label}
              onClick={() =>
                navigate(
                  item.to,
                  item.tour ? { state: { tour: item.tour } } : {},
                )
              }
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                {(item as any).explore ? (
                  <TourIcon color="action" fontSize="small" />
                ) : (item as any).done ? (
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

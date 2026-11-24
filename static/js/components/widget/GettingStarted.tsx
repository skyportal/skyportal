import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useJoyride, EVENTS } from "react-joyride";

import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Chip from "@mui/material/Chip";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import TourIcon from "@mui/icons-material/Tour";
import CloseIcon from "@mui/icons-material/Close";

import { showNotification } from "baselayer/components/Notifications";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useRequestGroupAdmissionMutation } from "../../ducks/groupAdmissionRequests";
import { useGetFiltersQuery } from "../../ducks/filter";
import { useFetchSourcesQuery } from "../../ducks/sources";
import { useGetRecentGcnEventsQuery } from "../../ducks/recentGcnEvents";
import { useAppDispatch } from "../../types/hooks";
import store from "../../store";
import { setSidebar } from "../../ducks/sidebar";
import { TOUR_STEPS } from "./GettingStartedTour";
import { useTourStyles } from "../tourStyles";
import WidgetCard from "./WidgetCard";

const MENU_TOUR_STEPS = TOUR_STEPS.filter(
  (step) => !String(step.target).includes("tour-getting-started"),
);

const useOnboardingTour = (steps: typeof TOUR_STEPS) => {
  const dispatch = useAppDispatch();
  const { options, styles } = useTourStyles();
  const { controls, on, Tour } = useJoyride({
    steps,
    continuous: true,
    // Scroll each target into view, including the first step.
    scrollToFirstStep: true,
    options,
    styles,
    locale: { last: "Got it" },
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

  return { startTour: () => controls.start(), Tour };
};

const useOnboarding = () => {
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
  const [requestGroupAdmission, { isLoading: isJoining }] =
    useRequestGroupAdmissionMutation();

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
  // The filter tour runs on a filter page; use the user's first filter.
  const firstFilterId = ((filters as any[] | undefined) ?? [])[0]?.id;

  // Open groups to encourage joining: auto-accept (one click admits you),
  // visible, not already a member, and whose required streams the user has.
  const isSysadmin = permissions.includes("System admin");
  const memberGroupIds = new Set((groups?.user ?? []).map((g: any) => g.id));
  const userStreamIds = new Set(
    ((profile as any)?.streams ?? []).map((s: any) => s.id),
  );
  const openGroups = ((groups?.all as any[] | null) ?? [])
    .filter(
      (g) =>
        g.auto_accept_requests &&
        !g.private &&
        !g.single_user_group &&
        !memberGroupIds.has(g.id) &&
        (isSysadmin ||
          (g.streams ?? []).every((s: any) => userStreamIds.has(s.id))),
    )
    .slice(0, 5);

  const handleJoinGroup = async (group: any) => {
    const { error } = await requestGroupAdmission({
      userID: (profile as any)?.id,
      groupID: group.id,
    });
    if (error) return;
    dispatch(showNotification(`Joined ${group.name}.`));
  };

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
      label: "Build filter logic",
      explore: true,
      to: firstFilterId ? `/filter/${firstFilterId}` : "/groups",
      tour: firstFilterId ? "filter" : undefined,
      help: "Combine conditions with AND/OR blocks to define which alerts pass your filter.",
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
    // Facility-management tours: ACL-gated, and no checkbox since there's no
    // per-user completion signal.
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

  const visibleChecklist = checklist.filter(
    (item) => !(item as any).acl || permissions.includes((item as any).acl),
  );
  const tracked = visibleChecklist.filter((item) => !(item as any).explore);
  const doneCount = tracked.filter((item) => (item as any).done).length;

  return {
    checklist: visibleChecklist,
    doneCount,
    total: tracked.length,
    openGroups,
    handleJoinGroup,
    isJoining,
  };
};

interface OnboardingChecklistProps {
  onboarding: ReturnType<typeof useOnboarding>;
  onNavigate?: () => void;
}

const OnboardingChecklist = ({
  onboarding,
  onNavigate,
}: OnboardingChecklistProps) => {
  const navigate = useNavigate();
  const {
    checklist,
    doneCount,
    total,
    openGroups,
    handleJoinGroup,
    isJoining,
  } = onboarding;

  return (
    <>
      {doneCount < total && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1.5 }}>
          <LinearProgress
            variant="determinate"
            value={(100 * doneCount) / total}
            sx={{ flex: 1, height: 6, borderRadius: 3 }}
          />
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ whiteSpace: "nowrap" }}
          >
            {doneCount} of {total} done
          </Typography>
        </Box>
      )}
      {openGroups.length > 0 && (
        <Box sx={{ mb: 1.5 }} data-testid="tour-getting-started-open-groups">
          <Typography variant="subtitle2" sx={{ mb: 0.75 }}>
            Open groups to join
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
            {openGroups.map((group) => (
              <Tooltip
                key={group.id}
                title={group.description || `Join ${group.name}`}
              >
                <Chip
                  label={group.name}
                  size="small"
                  variant="outlined"
                  clickable
                  disabled={isJoining}
                  onClick={() => handleJoinGroup(group)}
                  data-testid={`join-open-group-${group.id}`}
                />
              </Tooltip>
            ))}
          </Box>
        </Box>
      )}
      <List
        dense
        disablePadding
        data-testid="tour-getting-started-checklist"
        sx={{ mx: -1 }}
      >
        {checklist.map((item) => (
          <ListItemButton
            key={item.label}
            alignItems="flex-start"
            sx={{ px: 1, borderRadius: 2 }}
            onClick={() => {
              onNavigate?.();
              navigate(
                item.to,
                item.tour ? { state: { tour: item.tour } } : {},
              );
            }}
          >
            <ListItemIcon sx={{ minWidth: 30, mt: 0.5 }}>
              {(item as any).explore ? (
                <TourIcon color="action" fontSize="small" />
              ) : (item as any).done ? (
                <CheckCircleIcon color="success" fontSize="small" />
              ) : (
                <RadioButtonUncheckedIcon color="disabled" fontSize="small" />
              )}
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              secondary={item.help}
              slotProps={{
                primary: {
                  sx: {
                    fontWeight: 500,
                    color: (item as any).done
                      ? "text.secondary"
                      : "text.primary",
                  },
                },
              }}
            />
          </ListItemButton>
        ))}
      </List>
    </>
  );
};

const GettingStarted = () => {
  const onboarding = useOnboarding();
  const { startTour, Tour } = useOnboardingTour(TOUR_STEPS);
  const [updatePreferences] = useUpdateUserPreferencesMutation();
  const complete = onboarding.doneCount === onboarding.total;

  useEffect(() => {
    if (complete) updatePreferences({ onboardingDismissed: true });
  }, [complete, updatePreferences]);

  return (
    <WidgetCard
      testId="tour-getting-started"
      title="Getting started"
      actions={
        <>
          <Button
            size="small"
            data-testid="tour-start"
            onClick={startTour}
            sx={{ textTransform: "none", fontWeight: 600 }}
          >
            Take the tour
          </Button>
          <Tooltip title="Dismiss">
            <IconButton
              size="small"
              data-testid="tour-dismiss"
              onClick={() => updatePreferences({ onboardingDismissed: true })}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </>
      }
    >
      {Tour}
      <OnboardingChecklist onboarding={onboarding} />
    </WidgetCard>
  );
};

const GettingStartedDialogBody = ({
  onNavigate,
}: {
  onNavigate: () => void;
}) => (
  <OnboardingChecklist onboarding={useOnboarding()} onNavigate={onNavigate} />
);

export const GettingStartedDialog = ({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) => {
  const { startTour, Tour } = useOnboardingTour(MENU_TOUR_STEPS);

  return (
    <>
      {Tour}
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
        <DialogTitle
          sx={{ display: "flex", alignItems: "center", gap: 1, pr: 1.5 }}
        >
          <Box component="span" sx={{ flex: 1 }}>
            Getting started
          </Box>
          <Button
            size="small"
            onClick={() => {
              onClose();
              startTour();
            }}
            sx={{ textTransform: "none", fontWeight: 600 }}
          >
            Take the tour
          </Button>
          <IconButton size="small" aria-label="Close" onClick={onClose}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {open && <GettingStartedDialogBody onNavigate={onClose} />}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default GettingStarted;

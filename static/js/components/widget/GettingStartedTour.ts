import type { Step } from "react-joyride";

// Single source of truth for the "Getting Started" guided tour.
//
// The staleness test (skyportal/tests/api_tests/.../test_getting_started_tour.py)
// parses the `data-testid` selectors out of the targets below and asserts each
// one still exists somewhere in static/js. If a targeted element is renamed or
// removed, that test fails — so the tour can't silently go stale.
//
// Keep every target as a data-testid selector for that reason.
export const TOUR_STEPS: Step[] = [
  {
    target: '[data-testid="tour-getting-started"]',
    title: "Welcome to SkyPortal",
    content:
      "This is your Getting Started checklist. Work through the steps below — " +
      "or take this quick tour of the interface first.",
    placement: "center",
  },
  {
    target: '[data-testid="tour-sidebar"]',
    title: "Navigation",
    content:
      "Use the sidebar to reach Sources, Candidates, Groups, GCN Events, and " +
      "everything else.",
    // The drawer is tall and left-anchored; place the tooltip beside it.
    placement: "right",
  },
  {
    target: '[data-testid="tour-search"]',
    title: "Search",
    content:
      "Jump straight to any source, candidate, or GCN event by name from the " +
      "search bar.",
  },
  {
    target: '[data-testid="tour-nav-sources"]',
    title: "Sources",
    content:
      "Your saved objects live here. Each source page collects its photometry, " +
      "spectra, classifications, comments, and follow-up requests in one place.",
  },
  {
    target: '[data-testid="tour-nav-candidates"]',
    title: "Candidates",
    content:
      "Scan the alert stream here and save promising candidates as sources — " +
      "this is the core day-to-day workflow.",
  },
  {
    target: '[data-testid="tour-nav-groups"]',
    title: "Groups",
    content:
      "Groups control who sees what. Data in SkyPortal is shared at the group " +
      "level, so joining or creating a group is how you see and share sources.",
  },
  {
    target: '[data-testid="tour-nav-gcn"]',
    title: "GCN Events",
    content:
      "Multi-messenger alerts — gravitational-wave, neutrino, and gamma-ray — " +
      "land here with their sky localizations and observation plans.",
  },
  {
    target: '[data-testid="tour-getting-started-checklist"]',
    title: "Your checklist",
    content:
      "Complete these steps to get the most out of SkyPortal. You can reopen " +
      "this tour any time from the Getting Started widget.",
  },
];

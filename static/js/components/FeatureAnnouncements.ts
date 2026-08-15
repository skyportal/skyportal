import type { TourStep } from "./PageTours";

// One-time "what's new" popups. Each entry runs once per user, on the first
// matching page they open, then is marked seen in their preferences.
// Only display if the user is older than the announcedAt date.
export interface FeatureAnnouncement {
  // Stable key stored in preferences.featureAnnouncementsSeen; never reuse one.
  id: string;
  path: RegExp;
  announcedAt: string;
  steps: TourStep[];
}

export const FEATURE_ANNOUNCEMENTS: FeatureAnnouncement[] = [
  {
    id: "source-chat",
    path: /^\/source\/[^/]+$/,
    announcedAt: "2026-08-10",
    steps: [
      {
        target: '[data-testid="source-chat"]',
        title: "Comments are now a chat",
        content:
          "Comments got a refreshed look and now read like any messaging app, " +
          "newest at the bottom. Split side discussions into named " +
          "conversations with +, or detach the panel into a floating window.",
        placement: "top",
      },
    ],
  },
  {
    id: "alerts-sidebar-shortcut",
    path: /./,
    announcedAt: "2026-08-15",
    steps: [
      {
        // First: the Alerts step below is skipped without a default broker.
        target: '[data-testid="tour-nav-brokers"]',
        title: "New brokers page",
        content:
          "This takes you to the list of brokers set up for this instance. " +
          "Open whichever one you want from there to search its alerts.",
      },
      {
        target: '[data-testid="tour-nav-alerts"]',
        title: "New alerts shortcut",
        content:
          "This shortcut takes you straight to the alert search of this " +
          "instance's default broker.",
      },
    ],
  },
  {
    id: "brokers-page-alert-search",
    path: /^\/brokers\/?$/,
    announcedAt: "2026-08-15",
    steps: [
      {
        target: '[data-testid="tour-brokers-list"]',
        title: "New alert search",
        content:
          "Every broker set up for this instance is listed here. Open any of " +
          "them to search its alerts.",
      },
    ],
  },
];

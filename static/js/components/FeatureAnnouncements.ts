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
        target:
          '[data-testid="source-chat"], [data-testid="source-chat-button"]',
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
    id: "gcn-event-comments",
    path: /^\/gcn_events\/[^/]+$/,
    announcedAt: "2026-08-16",
    steps: [
      {
        target: '[data-testid="source-chat-button"]',
        title: "Comments on GCN events",
        content:
          "Event comments have moved to the new detached chat panel. Click this button to open it.",
        placement: "left",
      },
    ],
  },
  {
    id: "source-interests",
    path: /^\/source\/[^/]+$/,
    announcedAt: "2026-08-17",
    steps: [
      {
        target: '[data-testid="interested-button"]',
        title: "New interested button",
        content:
          "Register your interest in a source, with a note and a link to your " +
          "work. The button shows who else is interested, and opens a " +
          "conversation with them.",
      },
      {
        target: '[data-testid="discuss-interests-button"]',
        before: async () => {
          document
            .querySelector<HTMLElement>('[data-testid="interested-button"]')
            ?.click();
        },
        title: "Interested conversation",
        content:
          "Registering an interest opens a conversation dedicated to it in " +
          "the comments. Open it from here to plan the work together.",
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

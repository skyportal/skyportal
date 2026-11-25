import type { TourStep } from "./PageTours";

// One-time "what's new" popups. Each entry runs once per user, on the first
// matching page they open, then is marked seen in their preferences.
// Only display if the user is older than the announcedAt date.
export interface FeatureAnnouncement {
  // Stable key stored in preferences.featureAnnouncementsSeen; never reuse one.
  id: string;
  path: RegExp;
  announcedAt: string;
  requiresConfig?: string;
  steps: TourStep[];
}

export const FEATURE_ANNOUNCEMENTS: FeatureAnnouncement[] = [
  {
    id: "deployments-page",
    path: /./,
    announcedAt: "2026-09-30",
    steps: [
      {
        target: '[data-testid="tour-nav-other"]',
        before: async () => {
          const other = document.querySelector(
            '[data-testid="tour-nav-other"]',
          );
          if (!document.querySelector('[data-testid="tour-nav-deployments"]')) {
            other?.querySelector<HTMLElement>('[role="button"]')?.click();
            // wait for the menu's expand animation, so it can scroll into view
            await new Promise((resolve) => setTimeout(resolve, 450));
          }
          other?.scrollIntoView({ block: "center" });
        },
        title: "A new page in Other",
        content: "A new Deployments page is now available from this menu.",
      },
      {
        target: '[data-testid="tour-nav-deployments"]',
        before: async () => {
          if (!document.querySelector('[data-testid="tour-nav-deployments"]')) {
            document
              .querySelector<HTMLElement>(
                '[data-testid="tour-nav-other"] [role="button"]',
              )
              ?.click();
            await new Promise((resolve) => setTimeout(resolve, 450));
          }
          document
            .querySelector('[data-testid="tour-nav-deployments"]')
            ?.scrollIntoView({ block: "nearest" });
        },
        title: "Deployments",
        content:
          "See which version of the app is running and what changed with each " +
          "deployment.",
      },
    ],
  },
  {
    id: "discussions-page",
    path: /./,
    announcedAt: "2026-10-09",
    steps: [
      {
        target: '[data-testid="tour-nav-discussions"]',
        before: async () => {
          document
            .querySelector('[data-testid="tour-nav-discussions"]')
            ?.scrollIntoView({ block: "nearest" });
        },
        title: "Discussions",
        content:
          "All your conversations in one place: direct messages, group " +
          "discussions, and the comment threads you wrote in. Message anyone " +
          "from their profile, and choose how you are notified in your " +
          "notification preferences.",
      },
    ],
  },
  {
    id: "source-quick-save-buttons",
    path: /^\/source\/[^/]+$/,
    announcedAt: "2026-11-07",
    steps: [
      {
        target: '[data-testid^="editGroups_"]',
        title: "Several quick saves",
        content:
          "Set up as many quick save buttons as you need in your profile, " +
          "under Sources, each saving to its own groups. They show up next " +
          "to this button, which saves to any other group.",
      },
    ],
  },
  {
    id: "assignment-purpose",
    path: /^\/source\/[^/]+$/,
    announcedAt: "2026-11-13",
    steps: [
      {
        target: '[data-testid="assignmentPurposeSelect"]',
        before: async () => {
          document
            .querySelector('[data-testid="assignmentPurposeSelect"]')
            ?.scrollIntoView({ block: "center" });
        },
        title: "Assignment purpose",
        content:
          "Tag an observing run assignment as classification or follow-up. " +
          "The run page shows it in its own column and can filter on it.",
      },
    ],
  },
  {
    id: "feedback-header-button",
    path: /./,
    announcedAt: "2026-11-18",
    steps: [
      {
        target: '[data-testid="feedbackButton"]',
        title: "Feedback moved here",
        content:
          "Report a bug or ask for a new feature from this button, and " +
          "follow the replies on its page.",
        placement: "bottom",
      },
    ],
  },
];

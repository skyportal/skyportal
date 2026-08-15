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

export const FEATURE_ANNOUNCEMENTS: FeatureAnnouncement[] = [];

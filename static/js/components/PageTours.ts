import type { Step } from "react-joyride";

// Per-destination "how-to" tours. A Getting Started checklist item navigates
// with { state: { tour: <key> } }; PageTourProvider then runs the matching
// tour on the destination page.
//
// The staleness test parses the `data-testid` selectors below and asserts each
// still exists in static/js, so a renamed/removed anchor fails the test rather
// than silently breaking a tour. Keep every target as a data-testid selector.
export const PAGE_TOURS: Record<string, Step[]> = {
  profile: [
    {
      target: '[data-testid="tour-profile-info"]',
      title: "Your profile",
      content:
        "This is your profile. Add your name and affiliation so collaborators " +
        "know who you are.",
    },
    {
      target: '[data-testid="tour-profile-preferences"]',
      title: "Preferences & notifications",
      content:
        "Edit your details here, and choose how you want to be notified about " +
        "new sources, classifications, and GCN events.",
    },
    {
      target: '[data-testid="tour-profile-token"]',
      title: "API tokens",
      content:
        "Generate a token to query SkyPortal programmatically from scripts or " +
        "notebooks.",
    },
  ],
  groups: [
    {
      target: '[data-testid="tour-groups-list"]',
      title: "Your groups",
      content:
        "Groups you belong to appear here. Data in SkyPortal is shared at the " +
        "group level.",
    },
    {
      target: '[data-testid="tour-groups-new"]',
      title: "Create a group & add filters",
      content:
        "Create a new group here. Once you have one, open it to add an alert " +
        "filter and start collecting candidates.",
    },
  ],
  candidates: [
    {
      target: '[data-testid="tour-candidates-filter"]',
      title: "Scan candidates",
      content:
        "Pick a group and filter, then search. When you find a promising " +
        "candidate, use its Save button to save it as a source.",
    },
  ],
};

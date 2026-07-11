import type { Step } from "react-joyride";

// A tour step, optionally gated on an ACL. When `acl` is set, PageTourProvider
// drops the step for users whose profile.permissions doesn't include it, so
// permission-gated features (e.g. triggering follow-up, managing telescopes)
// only appear in the tour for users who can actually use them — and the tour
// never stalls waiting for a DOM target that isn't rendered for that user.
export type TourStep = Step & { acl?: string };

// Per-destination "how-to" tours. A Getting Started checklist item navigates
// with { state: { tour: <key> } }; PageTourProvider then runs the matching
// tour on the destination page.
//
// The staleness test parses the `data-testid` selectors below and asserts each
// still exists in static/js, so a renamed/removed anchor fails the test rather
// than silently breaking a tour. Keep every target as a data-testid selector.
export const PAGE_TOURS: Record<string, TourStep[]> = {
  profile: [
    {
      target: '[data-testid="tour-profile-info"]',
      title: "Your profile",
      content: "This is your profile at a glance.",
    },
    {
      target: '[data-testid="tour-profile-details"]',
      title: "Your details",
      content:
        "Set your name, contact info, and affiliations here so collaborators " +
        "know who you are.",
    },
    {
      target: '[data-testid="tour-profile-notifications"]',
      title: "Notifications",
      content:
        "Choose how you want to be notified about new sources, classifications, " +
        "and GCN events.",
    },
    {
      target: '[data-testid="tour-profile-appearance"]',
      title: "Appearance & display",
      content:
        "Tune the interface and default display settings to your liking.",
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
    {
      target: '[data-testid="tour-groups-request"]',
      title: "Join existing groups",
      content:
        "Groups you're not in are listed here — request admission and the " +
        "group's admin can approve you. As an admin, you approve requests and " +
        "add members from a group's own page.",
    },
  ],
  candidates: [
    {
      target: '[data-testid="tour-candidates-filter"]',
      title: "Scan candidates",
      content:
        "Pick a group and filter, then search to pull up candidates that " +
        "passed your alert filter over a date range.",
    },
    {
      target: '[data-testid="tour-candidate-save"]',
      title: "Save as a source",
      content:
        "Found something promising? Save the candidate as a source to one of " +
        "your groups — that's the core scanning workflow.",
    },
    {
      target: '[data-testid="tour-candidate-classifications"]',
      title: "Classify & annotate",
      content:
        "Add a classification, and review the filter's auto-annotations, right " +
        "from the scanning page to triage candidates quickly.",
    },
  ],
  // Runs on a source page (the checklist links to your first saved source).
  source: [
    {
      target: '[data-testid="tour-source-tns"]',
      title: "TNS name & reporting",
      content:
        "See whether this source is known to the Transient Name Server, and " +
        "submit a TNS report right from here (hover to reveal the action) to " +
        "announce a discovery or classification to the community.",
    },
    {
      target: '[data-testid="comments-accordion"]',
      title: "Comments",
      content:
        "Discuss a source with your collaborators. Comments can be public or " +
        "scoped to a single group, so you control who sees them.",
    },
    {
      target: '[data-testid="add-tag-button"]',
      title: "Labels & tags",
      content:
        "Tag a source (e.g. supernova, fast transient) to organize it. Tags " +
        "can be site-wide or private to your group.",
    },
    {
      target: '[data-testid="source-classifications"]',
      title: "Classifications",
      content:
        "Record and compare classifications for this source, with the " +
        "taxonomy and probability that back them up.",
    },
    {
      target: '[data-testid="show-photometry-table-button"]',
      title: "Photometry",
      content:
        "Open the photometry table to inspect every point, validate data, and " +
        "download it in a consistent format (with optional extinction " +
        "correction) for your analysis.",
    },
    {
      target: '[data-testid="tour-source-upload"]',
      title: "Add your own photometry",
      content:
        "Upload follow-up photometry — one point at a time or in bulk from a " +
        "CSV — and choose which groups it's shared with.",
    },
    {
      target: '[data-testid="tour-source-share"]',
      title: "Share data",
      content:
        "Share this source or its data with other groups or individual users. " +
        "Data stays private to your groups until you choose to share it.",
    },
    {
      target: '[data-testid="tour-source-followup"]',
      title: "Request follow-up",
      content:
        "Trigger follow-up observations on your instruments right from the " +
        "source page, and track each request's status here.",
    },
  ],
  telescopes: [
    {
      target: '[data-testid="tour-telescopes-map"]',
      title: "Telescopes",
      content:
        "Browse registered telescopes on the map or switch to the table view " +
        "to add your own (with its coordinates) if you have permission.",
      // The map fills the viewport; a centered tooltip avoids anchoring off-screen.
      placement: "center",
    },
  ],
  instruments: [
    {
      target: '[data-testid="tour-instruments-list"]',
      title: "Instruments",
      content:
        "Instruments registered on each telescope live here, along with their " +
        "filter lists and configuration.",
      // The table spans the page; center the tooltip so it can't fall off-screen.
      placement: "center",
    },
    {
      target: '[data-testid="tour-instruments-new"]',
      title: "Add an instrument",
      content:
        "Register an instrument on a telescope and set its filter list — that " +
        "filter list is what you'll pick from when uploading photometry or " +
        "requesting follow-up.",
      acl: "Manage instruments",
      // Add button sits in the top toolbar; keep the tooltip below it.
      placement: "bottom",
    },
  ],
  shifts: [
    {
      target: '[data-testid="tour-shifts-calendar"]',
      title: "Observing shifts",
      content:
        "Coordinate who's on duty. The calendar shows your team's scanning and " +
        "follow-up shifts.",
      placement: "center",
    },
    {
      target: '[data-testid="tour-shifts-new"]',
      title: "Schedule a shift",
      content:
        "Create a shift and assign members so everyone knows who's covering " +
        "scanning and follow-up.",
      acl: "Manage shifts",
      placement: "bottom",
    },
  ],
  // Runs on a single group's page (the checklist links to your first group).
  group: [
    {
      target: '[data-testid="description"]',
      title: "Your group",
      content:
        "This is a group's page. Everything in SkyPortal — sources, comments, " +
        "data — is shared at the group level, and this is where you manage it.",
    },
    {
      target: '[data-testid="tour-group-members"]',
      title: "Members & requests",
      content:
        "See the group's members. As an admin you can add existing users here " +
        "and approve or decline pending requests to join.",
    },
    {
      target: '[data-testid="tour-group-filters"]',
      title: "Streams & filters",
      content:
        "Attach alert streams and candidate filters to the group — this is what " +
        "feeds candidates into your scanning page.",
    },
  ],
  // Runs on a GCN event page (the checklist links to the most recent event).
  gcnevents: [
    {
      target: '[data-testid="tour-gcn-header"]',
      title: "GCN events",
      content:
        "Multi-messenger alerts — gravitational-wave, neutrino, gamma-ray — " +
        "with their sky localizations, tags, and properties.",
    },
    {
      target: '[data-testid="gcnsource-selection-form"]',
      title: "Find counterparts",
      content:
        "Query sources, galaxies, and observations that fall inside the event's " +
        "localization over a time window — the core of searching for a " +
        "counterpart.",
    },
    {
      target: '[data-testid="tour-gcn-obsplan"]',
      title: "Observation plans",
      content:
        "Generate and review observation plans that tile the localization with " +
        "your instruments to cover the most probable sky.",
    },
  ],
};

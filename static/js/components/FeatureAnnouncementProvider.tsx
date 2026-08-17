import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { EVENTS, useJoyride } from "react-joyride";
import type { Step } from "react-joyride";

import { FEATURE_ANNOUNCEMENTS } from "./FeatureAnnouncements";
import { useTourStyles } from "./tourStyles";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../ducks/profile";

const SEEN_PREF = "featureAnnouncementsSeen";

// App-level provider, mounted once inside the router: it runs the first
// announcement this user hasn't seen yet on the page they just opened.
const FeatureAnnouncementProvider = () => {
  const location = useLocation();
  const { data: profile } = useGetProfileQuery();
  const [updatePreferences] = useUpdateUserPreferencesMutation();
  const [steps, setSteps] = useState<Step[]>([]);
  const announcementID = useRef<string | null>(null);
  // Already run: profile.preferences only catches up after the mutation.
  const done = useRef<Set<string>>(new Set());
  const { options, styles } = useTourStyles();
  const { controls, on, Tour } = useJoyride({
    steps,
    continuous: true,
    scrollToFirstStep: true,
    // A single "what's new" step: no progress counter, just an acknowledgement.
    options: { ...options, showProgress: false },
    styles,
    locale: { last: "Got it", close: "Got it" },
  });

  useEffect(() => {
    if (!profile || profile.is_anonymous || announcementID.current) {
      return;
    }
    const permissions: string[] = profile.permissions ?? [];
    const seen = profile.preferences?.[SEEN_PREF] ?? {};
    const createdAt = profile.created_at ? new Date(profile.created_at) : null;
    const pending = FEATURE_ANNOUNCEMENTS.find(
      (announcement) =>
        !seen[announcement.id] &&
        !done.current.has(announcement.id) &&
        announcement.path.test(location.pathname) &&
        (!createdAt || createdAt < new Date(announcement.announcedAt)),
    );
    if (!pending) {
      return;
    }
    const applicable = pending.steps.filter(
      (step) => !step.acl || permissions.includes(step.acl),
    );
    if (!applicable.length) {
      return;
    }
    announcementID.current = pending.id;
    setSteps(applicable);
  }, [profile, location.pathname]);

  // Start only once the target has actually mounted, otherwise the tour runs
  // against an empty DOM and silently gives up.
  const startedFor = useRef<Step[] | null>(null);
  useEffect(() => {
    if (!steps.length || startedFor.current === steps) {
      return;
    }
    const firstTarget = steps[0]?.target;
    const target = typeof firstTarget === "string" ? firstTarget : null;
    let cancelled = false;
    let tries = 0;
    const startWhenReady = () => {
      if (cancelled) {
        return;
      }
      if (!target || document.querySelector(target)) {
        startedFor.current = steps;
        controls.start(0);
      } else if (tries++ < 100) {
        window.setTimeout(startWhenReady, 100);
      }
    };
    startWhenReady();
    return () => {
      cancelled = true;
    };
  }, [steps, controls]);

  useEffect(
    () =>
      on(EVENTS.TOUR_END, () => {
        if (announcementID.current) {
          updatePreferences({
            [SEEN_PREF]: { [announcementID.current]: true },
          });
          done.current.add(announcementID.current);
          announcementID.current = null;
        }
      }),
    [on, updatePreferences],
  );

  return <>{Tour}</>;
};

export default FeatureAnnouncementProvider;

import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useJoyride } from "react-joyride";
import type { Step } from "react-joyride";

import { PAGE_TOURS } from "./PageTours";
import { useTourStyles } from "./tourStyles";
import { useGetProfileQuery } from "../ducks/profile";

// Runs the tour requested by a navigation's { state: { tour: <key> } }, then
// clears the trigger so a refresh or back-navigation won't replay it.
const PageTourProvider = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { data: profile } = useGetProfileQuery();
  const [steps, setSteps] = useState<Step[]>([]);
  const { options, styles } = useTourStyles();
  const { controls, Tour } = useJoyride({
    steps,
    continuous: true,
    // Scroll each target into view, including the first step.
    scrollToFirstStep: true,
    options,
    styles,
    locale: { last: "Got it" },
  });

  const requested = (location.state as { tour?: string } | null)?.tour;
  // Steps tagged with an `acl` the user lacks target elements that aren't rendered.
  const permissions: string[] = (profile as any)?.permissions ?? [];
  useEffect(() => {
    if (requested && PAGE_TOURS[requested]) {
      setSteps(
        PAGE_TOURS[requested].filter(
          (step) => !step.acl || permissions.includes(step.acl),
        ),
      );
    }
    // permissions intentionally not a dep: filter with the ACLs loaded at launch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requested]);

  // Wait for the lazy-loaded page to mount the first target, otherwise the tour
  // runs against an empty DOM. The trigger is only cleared once we know the
  // outcome, so a slow-mounting page can still read location.state itself.
  const startedFor = useRef<Step[] | null>(null);
  useEffect(() => {
    if (!steps.length || startedFor.current === steps) {
      return;
    }
    const firstStep = steps[0];
    const firstTarget =
      firstStep && typeof firstStep.target === "string"
        ? firstStep.target
        : null;
    let cancelled = false;
    let tries = 0;
    const clearTrigger = () =>
      navigate(location.pathname + location.search + location.hash, {
        replace: true,
        state: {},
      });
    const startWhenReady = () => {
      if (cancelled) {
        return;
      }
      if (!firstTarget || document.querySelector(firstTarget)) {
        startedFor.current = steps;
        controls.start(0);
        clearTrigger();
      } else if (tries++ < 100) {
        // Poll ~every 100ms for up to ~10s while the page chunk loads.
        window.setTimeout(startWhenReady, 100);
      } else {
        // Target never appeared; drop the trigger so a refresh or
        // back-navigation doesn't keep retrying.
        clearTrigger();
      }
    };
    startWhenReady();
    return () => {
      cancelled = true;
    };
    // location/navigate read from the closure: keep the URL captured at poll start.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [steps, controls]);

  return <>{Tour}</>;
};

export default PageTourProvider;

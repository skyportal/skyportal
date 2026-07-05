import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useJoyride } from "react-joyride";
import type { Step } from "react-joyride";

import { PAGE_TOURS } from "./PageTours";

// App-level provider, mounted once inside the router so it survives navigation
// and can target the destination page. A Getting Started checklist item
// navigates with { state: { tour: <key> } }; we look up PAGE_TOURS[key], run it,
// then clear the trigger so a refresh or back-navigation won't replay it.
const PageTourProvider = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<Step[]>([]);
  const { controls, Tour } = useJoyride({
    steps,
    continuous: true,
    // Scroll each target into view, including the first step.
    scrollToFirstStep: true,
    // Lift above the app's low sidebar/modal z-indexes, give lazy-loaded pages
    // a little longer to mount a step's target, and show each tooltip directly
    // instead of a click-to-open beacon.
    options: { zIndex: 2000, targetWaitTimeout: 3000, skipBeacon: true },
  });

  const requested = (location.state as { tour?: string } | null)?.tour;
  useEffect(() => {
    if (requested && PAGE_TOURS[requested]) {
      setSteps(PAGE_TOURS[requested]);
      navigate(location.pathname + location.search + location.hash, {
        replace: true,
        state: {},
      });
    }
  }, [requested, location.pathname, location.search, location.hash, navigate]);

  // Start once per newly-selected step-set, but only after the destination
  // page (lazy-loaded behind Suspense) has actually mounted the first target —
  // otherwise the tour starts against an empty DOM and silently gives up.
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
    const startWhenReady = () => {
      if (cancelled) {
        return;
      }
      if (!firstTarget || document.querySelector(firstTarget)) {
        startedFor.current = steps;
        controls.start(0);
      } else if (tries++ < 100) {
        // Poll ~every 100ms for up to ~10s while the page chunk loads.
        window.setTimeout(startWhenReady, 100);
      }
    };
    startWhenReady();
    return () => {
      cancelled = true;
    };
  }, [steps, controls]);

  return <>{Tour}</>;
};

export default PageTourProvider;

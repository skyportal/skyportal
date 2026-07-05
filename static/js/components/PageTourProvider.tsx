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
    // Match the widget tour: lift above the app's low sidebar/modal z-indexes.
    options: { zIndex: 2000 },
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

  // Start once per newly-selected step-set (guarded so a stable-`controls`
  // identity change can't restart a running tour).
  const startedFor = useRef<Step[] | null>(null);
  useEffect(() => {
    if (steps.length && startedFor.current !== steps) {
      startedFor.current = steps;
      controls.start(0);
    }
  }, [steps, controls]);

  return <>{Tour}</>;
};

export default PageTourProvider;

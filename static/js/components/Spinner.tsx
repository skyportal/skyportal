import { useEffect, useState } from "react";

import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import { POST } from "../API";
import { useAppDispatch } from "../types/hooks";

// A placeholder that never resolves looks exactly like one that is about to, so
// after this long say the page may be stuck and offer a way out of it.
const STUCK_AFTER_MS = 15000;

const REPORT_STALL = "skyportal/REPORT_STALL";

interface SlowLoadNoticeProps {
  stuckAfterMs?: number;
  /** Named in the report, so the logs say which part of the app stalled. */
  context?: string | undefined;
}

/**
 * Shown by anything that stands in for content still loading -- the spinner
 * below, or a skeleton page -- once waiting has gone on long enough to suggest
 * something is wrong.
 */
export const SlowLoadNotice = ({
  stuckAfterMs = STUCK_AFTER_MS,
  context = "unknown",
}: SlowLoadNoticeProps) => {
  const [stuck, setStuck] = useState(false);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!stuckAfterMs) return undefined;
    const timer = setTimeout(() => {
      setStuck(true);
      // Report it: a page that hangs for one user is otherwise only heard
      // about if they think to say so.
      dispatch(
        POST("/api/internal/log", REPORT_STALL, {
          error: `Still loading after ${Math.round(stuckAfterMs / 1000)}s (${context})`,
          stack: ` at ${window.location.pathname}`,
        }),
      );
    }, stuckAfterMs);
    return () => clearTimeout(timer);
  }, [stuckAfterMs, context, dispatch]);

  if (!stuck) return null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.75rem",
        padding: "1rem",
      }}
    >
      <Typography variant="body2" color="textSecondary">
        This is taking longer than usual. The page may be stuck.
      </Typography>
      <Button
        size="small"
        variant="outlined"
        onClick={() => window.location.reload()}
      >
        Reload the page
      </Button>
    </div>
  );
};

const Spinner = ({
  stuckAfterMs = STUCK_AFTER_MS,
  context,
}: SlowLoadNoticeProps) => (
  <div
    style={{
      position: "fixed",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: "1rem",
      marginLeft: "auto",
      marginRight: "auto",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
    }}
  >
    <CircularProgress />
    <SlowLoadNotice stuckAfterMs={stuckAfterMs} context={context} />
  </div>
);

export default Spinner;

import { useEffect, useState } from "react";

import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

// A placeholder that never resolves looks exactly like one that is about to, so
// after this long say the page may be stuck and offer a way out of it.
const STUCK_AFTER_MS = 15000;

interface SlowLoadNoticeProps {
  stuckAfterMs?: number;
}

/**
 * Shown by anything that stands in for content still loading -- the spinner
 * below, or a skeleton page -- once waiting has gone on long enough to suggest
 * something is wrong.
 */
export const SlowLoadNotice = ({
  stuckAfterMs = STUCK_AFTER_MS,
}: SlowLoadNoticeProps) => {
  const [stuck, setStuck] = useState(false);

  useEffect(() => {
    if (!stuckAfterMs) return undefined;
    const timer = setTimeout(() => setStuck(true), stuckAfterMs);
    return () => clearTimeout(timer);
  }, [stuckAfterMs]);

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

const Spinner = ({ stuckAfterMs = STUCK_AFTER_MS }: SlowLoadNoticeProps) => (
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
    <SlowLoadNotice stuckAfterMs={stuckAfterMs} />
  </div>
);

export default Spinner;

import { useEffect, useState } from "react";

import Backdrop from "@mui/material/Backdrop";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { POST } from "../API";
import { useAppDispatch } from "../types/hooks";

const STUCK_AFTER_MS = 15000;

const REPORT_STALL = "skyportal/REPORT_STALL";

const BEHIND_SIDEBAR_AND_TOP_BAR = 130;

interface SlowLoadNoticeProps {
  stuckAfterMs?: number;
  context?: string | undefined;
  overlay?: boolean | undefined;
}

export const SlowLoadNotice = ({
  stuckAfterMs = STUCK_AFTER_MS,
  context = "unknown",
  overlay = false,
}: SlowLoadNoticeProps) => {
  const [stuck, setStuck] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!stuckAfterMs) return undefined;
    const timer = setTimeout(() => {
      setStuck(true);
      dispatch(
        POST("/api/internal/log", REPORT_STALL, {
          error: `Still loading after ${Math.round(stuckAfterMs / 1000)}s (${context})`,
          stack: ` at ${window.location.pathname}`,
        }),
      );
    }, stuckAfterMs);
    return () => clearTimeout(timer);
  }, [stuckAfterMs, context, dispatch]);

  if (!stuck || dismissed) return null;

  const notice = (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 1.5,
        padding: 2,
      }}
    >
      <Typography>
        This is taking longer than usual. The page may be stuck.
      </Typography>
      <Button
        size="small"
        variant="outlined"
        onClick={() => window.location.reload()}
      >
        Reload the page
      </Button>
    </Box>
  );

  if (!overlay) return notice;

  return (
    <Backdrop
      open
      sx={{ zIndex: BEHIND_SIDEBAR_AND_TOP_BAR }}
      onClick={() => setDismissed(true)}
    >
      <Paper
        elevation={8}
        sx={{ paddingX: 2 }}
        onClick={(event) => event.stopPropagation()}
      >
        {notice}
      </Paper>
    </Backdrop>
  );
};

const Spinner = ({
  stuckAfterMs = STUCK_AFTER_MS,
  context,
}: SlowLoadNoticeProps) => (
  <Box
    sx={{
      position: "fixed",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 2,
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
    }}
  >
    <CircularProgress />
    <SlowLoadNotice stuckAfterMs={stuckAfterMs} context={context} />
  </Box>
);

export default Spinner;

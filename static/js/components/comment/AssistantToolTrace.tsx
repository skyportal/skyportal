import { useState } from "react";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";

import { AssistantToolCall } from "../../ducks/assistant";
import { linkButtonSx } from "./assistantStyles";

// The arguments worth showing in the one-line summary of a call. A pipeline is
// the whole point of the call it appears in, and is shown in the proposal.
const KEY_ARGS = ["survey", "search", "prefix", "name", "filter_id", "fid"];

const describe = (call: AssistantToolCall) => {
  const shown = KEY_ARGS.filter((k) => call.arguments?.[k] != null).map(
    (k) => `${k}: ${call.arguments[k]}`,
  );
  return shown.join(", ");
};

interface AssistantToolTraceProps {
  calls: AssistantToolCall[];
}

const AssistantToolTrace = ({ calls }: AssistantToolTraceProps) => {
  const [open, setOpen] = useState(false);
  if (!calls?.length) return null;

  const failed = calls.filter((call) => !call.ok).length;

  return (
    <Box sx={{ marginBottom: "0.5rem" }}>
      <Box
        component="button"
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        sx={linkButtonSx}
      >
        <span>
          {calls.length} {calls.length === 1 ? "step" : "steps"}
          {failed > 0 && (
            <Box component="span" sx={{ color: "error.main" }}>
              , {failed} failed
            </Box>
          )}
        </span>
        <ExpandMoreIcon
          sx={{
            fontSize: "1rem",
            transition: "transform 150ms",
            transform: open ? "rotate(180deg)" : "none",
          }}
        />
      </Box>
      <Collapse in={open} unmountOnExit>
        <Box
          component="ol"
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
            listStyle: "none",
            margin: "0.4rem 0 0.25rem 0.25rem",
            padding: "0 0 0 0.85rem",
            borderLeft: 2,
            borderColor: "divider",
          }}
        >
          {calls.map((call, index) => (
            <Box
              component="li"
              key={`${call.name}-${index}`}
              sx={{ position: "relative", fontSize: "0.75rem", minWidth: 0 }}
            >
              <Box
                title={call.ok ? "Succeeded" : "Failed"}
                sx={(theme) => ({
                  position: "absolute",
                  left: "calc(-0.85rem - 5px)",
                  top: "0.4rem",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: call.ok
                    ? theme.palette.success.main
                    : theme.palette.error.main,
                  boxShadow: `0 0 0 2px ${theme.palette.background.paper}`,
                })}
              />
              <Box component="code" sx={{ fontWeight: 600 }}>
                {call.name}
              </Box>
              {describe(call) && (
                <Box component="span" sx={{ color: "text.secondary" }}>
                  {" "}
                  {describe(call)}
                </Box>
              )}
              <Box sx={{ color: "text.secondary", overflowWrap: "anywhere" }}>
                {call.summary}
              </Box>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
};

export default AssistantToolTrace;

import { Fragment } from "react";

import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import ErrorOutlinedIcon from "@mui/icons-material/ErrorOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import { AssistantToolCall } from "../../ducks/assistant";

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
  if (!calls?.length) return null;

  const failed = calls.filter((call) => !call.ok).length;

  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={(theme) => ({
        marginRight: "1rem",
        marginBottom: "0.25rem",
        backgroundColor: alpha(theme.palette.text.primary, 0.03),
        "&::before": { display: "none" },
      })}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem" }} />}
        sx={{ minHeight: 0, "& .MuiAccordionSummary-content": { margin: 0 } }}
      >
        <Typography sx={{ fontSize: "0.7rem", opacity: 0.6 }}>
          {calls.length} {calls.length === 1 ? "step" : "steps"}
          {failed > 0 && `, ${failed} failed`}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ paddingTop: 0 }}>
        {calls.map((call, index) => (
          <Fragment key={`${call.name}-${index}`}>
            <Box
              sx={{
                display: "flex",
                alignItems: "baseline",
                gap: "0.35rem",
                fontSize: "0.7rem",
                marginBottom: "0.35rem",
              }}
            >
              {call.ok ? (
                <CheckCircleOutlinedIcon
                  color="success"
                  sx={{ fontSize: "0.85rem" }}
                />
              ) : (
                <ErrorOutlinedIcon color="error" sx={{ fontSize: "0.85rem" }} />
              )}
              <Box sx={{ minWidth: 0 }}>
                <Box component="code" sx={{ fontWeight: 600 }}>
                  {call.name}
                </Box>
                {describe(call) && (
                  <Box component="span" sx={{ opacity: 0.6 }}>
                    {" "}
                    {describe(call)}
                  </Box>
                )}
                <Box
                  sx={{
                    opacity: 0.55,
                    overflowWrap: "anywhere",
                    marginTop: "0.1rem",
                  }}
                >
                  {call.summary}
                </Box>
              </Box>
            </Box>
          </Fragment>
        ))}
      </AccordionDetails>
    </Accordion>
  );
};

export default AssistantToolTrace;

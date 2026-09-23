import { lazy, Suspense } from "react";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Typography from "@mui/material/Typography";

import { useGetConfigQuery } from "../../ducks/config";

const CommentPanel = lazy(() => import("../comment/CommentPanel"));

// The assistant docked above the builder. It reads the filter it is sitting on
// from the comment-panel target the page already sets.
const BrokerFilterAssistant = () => {
  const enabled = useGetConfigQuery().data?.["assistantEnabled"] === true;
  if (!enabled) return null;

  return (
    <Accordion defaultExpanded sx={{ mb: 1 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography>Assistant</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Suspense fallback={null}>
          <CommentPanel inline assistant />
        </Suspense>
      </AccordionDetails>
    </Accordion>
  );
};

export default BrokerFilterAssistant;

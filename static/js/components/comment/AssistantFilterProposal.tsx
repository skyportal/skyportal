import { useState } from "react";
import { useParams } from "react-router-dom";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { AssistantProposal } from "../../ducks/assistant";
import {
  useBoomFilterVersion,
  useUpdateBoomGroupFilterMutation,
} from "../../ducks/boom_filter";
import { decompilePipeline } from "../../utils/mongoPipelineDecompiler";

const matchCount = (summary: string) => {
  try {
    const count = JSON.parse(summary)?.count;
    return typeof count === "number" ? count : null;
  } catch {
    return null;
  }
};

interface AssistantFilterProposalProps {
  proposal: AssistantProposal;
}

// A pipeline the assistant built and previewed, offered for saving. Saving goes
// through the same endpoint the builder's own Save does, so the new version is
// validated on arrival and still has to be activated by hand.
const AssistantFilterProposal = ({
  proposal,
}: AssistantFilterProposalProps) => {
  const { fid } = useParams();
  const [saveFilter, { isLoading }] = useUpdateBoomGroupFilterMutation();
  const { refetch } = useBoomFilterVersion();
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const alreadySaved = proposal.target != null;
  const count = matchCount(proposal.preview?.summary ?? "");
  // A tree is stored only when it compiles back to this exact pipeline, so the
  // builder can never show something the broker would not run. Without one the
  // version loads read-only, as an imported pipeline does.
  const tree = decompilePipeline(proposal.pipeline);

  const handleSave = async () => {
    setError(null);
    try {
      await saveFilter({
        filter_id: fid,
        altdata: proposal.pipeline,
        ...(tree ? { filters: { filters: tree, projectionFields: [] } } : {}),
      }).unwrap();
      setSaved(true);
      refetch();
    } catch (e: any) {
      setError(e?.data?.message ?? "Could not save this version.");
    }
  };

  return (
    <Paper
      variant="outlined"
      sx={{ marginRight: "1rem", marginBottom: "0.5rem", padding: "0.5rem" }}
    >
      <Typography sx={{ fontSize: "0.75rem", fontWeight: 600 }}>
        Proposed filter
      </Typography>
      <Typography sx={{ fontSize: "0.7rem", opacity: 0.7 }}>
        {count === null
          ? "Previewed on the broker."
          : `Matched ${count.toLocaleString()} alerts in the previewed window.`}
      </Typography>

      <Accordion
        disableGutters
        elevation={0}
        sx={{
          backgroundColor: "transparent",
          "&::before": { display: "none" },
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem" }} />}
          sx={{
            minHeight: 0,
            padding: 0,
            "& .MuiAccordionSummary-content": { margin: 0 },
          }}
        >
          <Typography sx={{ fontSize: "0.7rem", opacity: 0.6 }}>
            Pipeline
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ padding: 0 }}>
          <Box
            component="pre"
            sx={{
              fontSize: "0.65rem",
              maxHeight: "12rem",
              overflow: "auto",
              margin: 0,
            }}
          >
            {JSON.stringify(proposal.pipeline, null, 2)}
          </Box>
        </AccordionDetails>
      </Accordion>

      {error && (
        <Alert
          severity="error"
          sx={{ fontSize: "0.7rem", marginTop: "0.25rem" }}
        >
          {error}
        </Alert>
      )}

      {alreadySaved || saved ? (
        <Typography sx={{ fontSize: "0.7rem", opacity: 0.7 }}>
          Saved as a new version. Validate and activate it below.
        </Typography>
      ) : tree ? (
        <Button size="small" onClick={handleSave} disabled={isLoading}>
          Save as a new version
        </Button>
      ) : (
        <>
          <Typography sx={{ fontSize: "0.7rem", opacity: 0.7 }}>
            Uses more than the builder can show, so it saves read-only.
          </Typography>
          <Button size="small" onClick={handleSave} disabled={isLoading}>
            Save as a new version
          </Button>
        </>
      )}
    </Paper>
  );
};

export default AssistantFilterProposal;

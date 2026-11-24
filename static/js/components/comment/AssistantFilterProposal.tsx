import { type ReactNode, useState } from "react";
import { useParams } from "react-router-dom";

import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import { useCommentPanel } from "../../contexts/CommentPanelContext";
import { AssistantProposal } from "../../ducks/assistant";
import {
  useBoomFilterVersion,
  useUpdateBoomGroupFilterMutation,
} from "../../ducks/boom_filter";
import { decompilePipeline } from "../../utils/mongoPipelineDecompiler";
import LasairFilterProposal from "../broker/lasair/LasairFilterProposal";
import NewFilterDialog from "../filter/NewFilterDialog";
import {
  cardNoteSx,
  cardSx,
  cardTitleSx,
  chevronSx,
  linkButtonSx,
  pillButtonSx,
} from "./chatStyles";

const matchCount = (summary: string) => {
  try {
    const count = JSON.parse(summary)?.count;
    return typeof count === "number" ? count : null;
  } catch {
    return null;
  }
};

// A tree is stored only when it compiles back to this exact pipeline, so the
// builder can never show something the broker would not run. Without one the
// version loads read-only, as an imported pipeline does.
const versionOf = (pipeline: any[]): { altdata: any[]; filters?: any } => {
  const tree = decompilePipeline(pipeline);
  return {
    altdata: pipeline,
    ...(tree ? { filters: { filters: tree, projectionFields: [] } } : {}),
  };
};

const ReadOnlyNote = () => (
  <Typography sx={cardNoteSx}>
    Uses more than the builder can show, so it saves read-only.
  </Typography>
);

interface AssistantFilterProposalProps {
  proposal: AssistantProposal;
}

const ProposalCard = ({
  proposal,
  children,
}: AssistantFilterProposalProps & { children: ReactNode }) => {
  const [showPipeline, setShowPipeline] = useState(false);
  const count = matchCount(proposal.preview?.summary ?? "");
  return (
    <Box sx={cardSx}>
      <Box>
        <Typography sx={cardTitleSx}>Proposed filter</Typography>
        <Typography sx={cardNoteSx}>
          {count === null
            ? "Previewed on the broker."
            : `Matched ${count.toLocaleString()} alerts in the previewed window.`}
        </Typography>
      </Box>
      <Box
        component="button"
        type="button"
        aria-expanded={showPipeline}
        onClick={() => setShowPipeline(!showPipeline)}
        sx={linkButtonSx}
      >
        Pipeline
        <ExpandMoreIcon sx={chevronSx(showPipeline)} />
      </Box>
      <Collapse in={showPipeline} unmountOnExit sx={{ alignSelf: "stretch" }}>
        <Box
          component="pre"
          sx={(theme) => ({
            margin: 0,
            padding: "0.5rem 0.65rem",
            maxHeight: "12rem",
            overflow: "auto",
            fontSize: "0.7rem",
            borderRadius: "8px",
            backgroundColor: alpha(theme.palette.text.primary, 0.05),
          })}
        >
          {JSON.stringify(proposal.pipeline, null, 2)}
        </Box>
      </Collapse>
      {children}
    </Box>
  );
};

// A pipeline the assistant built and previewed, offered for saving. Saving goes
// through the same endpoint the builder's own Save does, so the new version is
// validated on arrival and still has to be activated by hand.
const PipelineFilterProposal = ({ proposal }: AssistantFilterProposalProps) => {
  const { fid } = useParams();
  const [saveFilter, { isLoading }] = useUpdateBoomGroupFilterMutation();
  const { refetch } = useBoomFilterVersion();
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const alreadySaved = proposal.target != null;
  const version = versionOf(proposal.pipeline);

  const handleSave = async () => {
    setError(null);
    try {
      await saveFilter({ filter_id: fid, ...version }).unwrap();
      setSaved(true);
      refetch();
    } catch (e: any) {
      setError(e?.data?.message ?? "Could not save this version.");
    }
  };

  return (
    <ProposalCard proposal={proposal}>
      {error && (
        <Alert
          severity="error"
          sx={{ alignSelf: "stretch", fontSize: "0.75rem" }}
        >
          {error}
        </Alert>
      )}

      {alreadySaved || saved ? (
        <Typography sx={cardNoteSx}>
          Saved as a new version. Validate and activate it below.
        </Typography>
      ) : (
        <>
          {!version.filters && <ReadOnlyNote />}
          <Button
            size="small"
            variant="contained"
            disableElevation
            onClick={handleSave}
            disabled={isLoading}
            sx={pillButtonSx}
          >
            Save as a new version
          </Button>
        </>
      )}
    </ProposalCard>
  );
};

const NewFilterProposal = ({
  proposal,
  brokerId,
}: AssistantFilterProposalProps & { brokerId: number }) => {
  const [open, setOpen] = useState(false);
  const version = versionOf(proposal.pipeline);

  return (
    <ProposalCard proposal={proposal}>
      {!version.filters && <ReadOnlyNote />}
      <Button
        size="small"
        variant="contained"
        disableElevation
        onClick={() => setOpen(true)}
        sx={pillButtonSx}
      >
        Create filter
      </Button>
      <NewFilterDialog
        open={open}
        onClose={() => setOpen(false)}
        brokerId={brokerId}
        version={version}
      />
    </ProposalCard>
  );
};

const AssistantFilterProposal = ({
  proposal,
}: AssistantFilterProposalProps) => {
  const { target } = useCommentPanel();
  if (target?.type === "filter") {
    return proposal.lasair ? (
      <LasairFilterProposal proposal={proposal} />
    ) : (
      <PipelineFilterProposal proposal={proposal} />
    );
  }
  if (proposal.lasair || proposal.target || proposal.broker_id == null) {
    return null;
  }
  return (
    <NewFilterProposal proposal={proposal} brokerId={proposal.broker_id} />
  );
};

export default AssistantFilterProposal;

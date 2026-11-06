import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { useCommentPanel } from "../../../contexts/CommentPanelContext";
import { AssistantProposal } from "../../../ducks/assistant";
import { useSaveBrokerFilterMutation } from "../../../ducks/brokers";
import { asRootBlocks } from "./lasairTree";

interface LasairFilterProposalProps {
  proposal: AssistantProposal;
}

const LasairFilterProposal = ({ proposal }: LasairFilterProposalProps) => {
  const { target } = useCommentPanel();
  const [saveFilter, { isLoading }] = useSaveBrokerFilterMutation();
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { broker_id, tree, count } = proposal.lasair!;

  const apply = async () => {
    if (target?.type !== "filter") return;
    setError(null);
    try {
      await saveFilter({
        brokerId: broker_id,
        filterId: target.id,
        query: { tree: asRootBlocks(tree) },
      }).unwrap();
      setApplied(true);
    } catch (e: any) {
      setError(e?.data?.message ?? "Could not apply this filter.");
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
          ? "Previewed on Lasair."
          : `Matched ${count.toLocaleString()} objects on Lasair.`}
      </Typography>
      {error && (
        <Alert
          severity="error"
          sx={{ fontSize: "0.7rem", marginTop: "0.25rem" }}
        >
          {error}
        </Alert>
      )}
      {applied ? (
        <Typography sx={{ fontSize: "0.7rem", opacity: 0.7 }}>
          Applied to the builder.
        </Typography>
      ) : (
        <Button size="small" onClick={apply} disabled={isLoading}>
          Apply to the builder
        </Button>
      )}
    </Paper>
  );
};

export default LasairFilterProposal;

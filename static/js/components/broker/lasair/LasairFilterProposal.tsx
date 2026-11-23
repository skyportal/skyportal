import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";

import { useCommentPanel } from "../../../contexts/CommentPanelContext";
import { AssistantProposal } from "../../../ducks/assistant";
import { useSaveBrokerFilterMutation } from "../../../ducks/brokers";
import {
  cardNoteSx,
  cardSx,
  cardTitleSx,
  pillButtonSx,
} from "../../comment/assistantStyles";
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
    <Box sx={cardSx}>
      <Box>
        <Typography sx={cardTitleSx}>Proposed filter</Typography>
        <Typography sx={cardNoteSx}>
          {count === null
            ? "Previewed on Lasair."
            : `Matched ${count.toLocaleString()} objects on Lasair.`}
        </Typography>
      </Box>
      {error && (
        <Alert
          severity="error"
          sx={{ alignSelf: "stretch", fontSize: "0.75rem" }}
        >
          {error}
        </Alert>
      )}
      {applied ? (
        <Typography sx={cardNoteSx}>Applied to the builder.</Typography>
      ) : (
        <Button
          size="small"
          variant="contained"
          disableElevation
          onClick={apply}
          disabled={isLoading}
          sx={pillButtonSx}
        >
          Apply to the builder
        </Button>
      )}
    </Box>
  );
};

export default LasairFilterProposal;

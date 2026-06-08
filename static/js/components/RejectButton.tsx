import { useState } from "react";

import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import Tooltip from "@mui/material/Tooltip";

import {
  useGetRejectedCandidatesQuery,
  useAddToRejectedMutation,
  useRemoveFromRejectedMutation,
} from "../ducks/rejected_candidates";

const ButtonVisible = (objID: string) => {
  const [addToRejected] = useAddToRejectedMutation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await addToRejected(objID).unwrap();
    } catch {
      // error notification handled centrally by the base query
    }
    setIsSubmitting(false);
  };
  return (
    <Tooltip title="click to hide candidate from scanning page">
      <IconButton
        onClick={handleSubmit}
        data-testid={`rejected-visible_${objID}`}
        disabled={isSubmitting}
        size="small"
      >
        <VisibilityIcon />
      </IconButton>
    </Tooltip>
  );
};

const ButtonInvisible = (objID: string) => {
  const [removeFromRejected] = useRemoveFromRejectedMutation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await removeFromRejected(objID).unwrap();
    } catch {
      // error notification handled centrally by the base query
    }
    setIsSubmitting(false);
  };

  return (
    <Tooltip title="click to make candidate visible on scanning page">
      <IconButton
        onClick={handleSubmit}
        data-testid={`rejected_invisible_${objID}`}
        disabled={isSubmitting}
        size="small"
      >
        <VisibilityOffIcon />
      </IconButton>
    </Tooltip>
  );
};

interface RejectButtonProps {
  objID: string;
}

const RejectButton = ({ objID }: RejectButtonProps) => {
  const { data: rejected_candidates } = useGetRejectedCandidatesQuery();

  if (!objID) {
    return null;
  }
  if ((rejected_candidates ?? []).includes(objID)) {
    return ButtonInvisible(objID);
  }
  return ButtonVisible(objID);
};

export default RejectButton;

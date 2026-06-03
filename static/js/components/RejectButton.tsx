import { useState } from "react";

import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import Tooltip from "@mui/material/Tooltip";

import { useAppDispatch, useAppSelector } from "../types/hooks";
import * as Actions from "../ducks/rejected_candidates";

const ButtonVisible = (objID: string) => {
  const dispatch = useAppDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    await dispatch(Actions.addToRejected(objID));
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
  const dispatch = useAppDispatch();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSubmit = async () => {
    setIsSubmitting(true);
    await dispatch(Actions.removeFromRejected(objID));
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
  const { rejected_candidates } = useAppSelector(
    (state) => state["rejected_candidates"],
  );

  if (!objID) {
    return null;
  }
  if (rejected_candidates.includes(objID)) {
    return ButtonInvisible(objID);
  }
  return ButtonVisible(objID);
};

export default RejectButton;

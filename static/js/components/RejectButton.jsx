import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";
import IconButton from "@mui/material/IconButton";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import Tooltip from "@mui/material/Tooltip";

import * as Actions from "../ducks/rejected_candidates";

const ButtonVisible = (objID) => {
  const dispatch = useDispatch();
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

const ButtonInvisible = (objID) => {
  const dispatch = useDispatch();
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

const RejectButton = ({ objID }) => {
  const { rejected_candidates } = useSelector(
    (state) => state.rejected_candidates,
  );

  if (!objID) {
    return null;
  }
  if (rejected_candidates.includes(objID)) {
    return ButtonInvisible(objID);
  }
  return ButtonVisible(objID);
};

RejectButton.propTypes = {
  objID: PropTypes.string.isRequired,
};

export default RejectButton;

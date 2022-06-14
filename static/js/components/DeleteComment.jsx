import React from "react";
import { useDispatch } from "react-redux";

import PropTypes from "prop-types";

import { Button } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

import * as sourceActions from "../ducks/source";
import * as gcnEventActions from "../ducks/gcnEvent";
import * as shiftActions from "../ducks/shift";

const DeleteComment = ({
  associatedResourceType = "object",
  objID = null,
  gcnEventID = null,
  spectrum_id = null,
  id = null,
  hoverID = null,
  shift_id = null,
}) => {
  const dispatch = useDispatch();
  const deleteCommentOnObject = (sourceID, commentID) => {
    dispatch(sourceActions.deleteComment(sourceID, commentID));
  };

  const deleteCommentOnSpectrum = (commentSpectrumID, commentID) => {
    dispatch(
      sourceActions.deleteCommentOnSpectrum(commentSpectrumID, commentID)
    );
  };

  const deleteCommentOnGcnEvent = (gcnID, commentID) => {
    dispatch(gcnEventActions.deleteCommentOnGcnEvent(gcnID, commentID));
  };

  const deleteCommentOnShift = (shiftID, commentID) => {
    dispatch(shiftActions.deleteCommentOnShift(shiftID, commentID));
  };

  const deleteComment = (resourceType) => {
    switch (resourceType) {
      case "object":
        deleteCommentOnObject(objID, id);
        break;
      case "spectrum":
        deleteCommentOnSpectrum(spectrum_id, id);
        break;
      case "gcnEvent":
        deleteCommentOnGcnEvent(gcnEventID, id);
        break;
      case "shift":
        deleteCommentOnShift(shift_id, id);
        break;
      default:
        break;
    }
  };

  return (
    <>
      <Button
        style={
          hoverID === id
            ? {
                display: "block",
                minWidth: "0",
                lineHeight: "0",
                padding: "0",
              }
            : { display: "none" }
        }
        size="small"
        color="primary"
        type="button"
        name={`deleteCommentButton${id}`}
        onClick={() => deleteComment(associatedResourceType)}
        className="commentDelete"
      >
        <CloseIcon fontSize="small" />
      </Button>
    </>
  );
};

DeleteComment.propTypes = {
  associatedResourceType: PropTypes.string,
  objID: PropTypes.string,
  gcnEventID: PropTypes.string,
  spectrum_id: PropTypes.string,
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  hoverID: PropTypes.number,
  shift_id: PropTypes.number,
};

DeleteComment.defaultProps = {
  associatedResourceType: "object",
  objID: null,
  gcnEventID: null,
  spectrum_id: null,
  id: null,
  hoverID: null,
  shift_id: null,
};

export default DeleteComment;

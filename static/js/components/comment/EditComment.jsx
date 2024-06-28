import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";

import EditIcon from "@mui/icons-material/Edit";
import Button from "../Button";
import CommentEntry from "./CommentEntry";

import * as sourceActions from "../../ducks/source";
import * as gcnEventActions from "../../ducks/gcnEvent";
import * as shiftActions from "../../ducks/shift";

const EditComment = ({
  associatedResourceType = "object",
  objID = null,
  gcnEventID = null,
  spectrum_id = null,
  id = null,
  hoverID = null,
  shiftID = null,
  commentText = "",
  attachmentName = "",
}) => {
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const closeDialog = () => {
    setDialogOpen(false);
  };

  const editCommentOnObject = (sourceID, commentID, formData) => {
    formData.obj_id = sourceID;
    dispatch(sourceActions.editComment(commentID, formData));
  };

  const editCommentOnSpectrum = (spectrumID, commentID, formData) => {
    formData.spectrum_id = spectrumID;
    dispatch(sourceActions.editComment(commentID, formData));
  };

  const editCommentOnGcnEvent = (gcnID, commentID, formData) => {
    dispatch(gcnEventActions.editCommentOnGcnEvent(commentID, gcnID, formData));
  };

  const editCommentOnShift = (shift_id, commentID, formData) => {
    formData.shift_id = shift_id;
    dispatch(shiftActions.editCommentOnShift(commentID, formData));
  };

  const editComment = (data) => {
    switch (associatedResourceType) {
      case "object":
        editCommentOnObject(objID, id, data);
        break;
      case "spectrum":
        editCommentOnSpectrum(spectrum_id, id, data);
        break;
      case "gcn_event":
        editCommentOnGcnEvent(gcnEventID, id, data);
        break;
      case "shift":
        editCommentOnShift(shiftID, id, data);
        break;
      default:
        break;
    }
  };

  return (
    <div>
      <div>
        <Button
          primary
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
          type="button"
          name={`editCommentButton${id}`}
          onClick={() => setDialogOpen(true)}
          className="commentEdit"
        >
          <EditIcon fontSize="small" />
        </Button>
      </div>
      <div>
        <Dialog
          sx={{ "z-index": 99999 }}
          open={dialogOpen}
          onClose={closeDialog}
        >
          <DialogContent>
            <CommentEntry
              editComment={editComment}
              commentText={commentText}
              attachmentName={attachmentName}
              closeDialog={closeDialog}
            />
          </DialogContent>
          <DialogActions>
            <Button secondary autoFocus onClick={closeDialog}>
              Dismiss
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

EditComment.propTypes = {
  associatedResourceType: PropTypes.string,
  objID: PropTypes.string,
  gcnEventID: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  spectrum_id: PropTypes.string,
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  hoverID: PropTypes.number,
  shiftID: PropTypes.number,
  commentText: PropTypes.string,
  attachmentName: PropTypes.string,
};

EditComment.defaultProps = {
  associatedResourceType: "object",
  objID: null,
  gcnEventID: null,
  spectrum_id: null,
  id: null,
  hoverID: null,
  shiftID: null,
  commentText: "",
  attachmentName: "",
};

export default EditComment;

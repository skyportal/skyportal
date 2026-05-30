import React, { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";

import EditIcon from "@mui/icons-material/Edit";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import CommentEntry from "./CommentEntry";

import * as sourceActions from "../../ducks/source";
import * as gcnEventActions from "../../ducks/gcnEvent";
import * as shiftsActions from "../../ducks/shifts";

interface EditCommentProps {
  associatedResourceType?: string;
  objID?: string | null;
  gcnEventID?: string | number | null;
  spectrum_id?: string | null;
  id?: string | number | null;
  hoverID?: number | null;
  shiftID?: number | null;
  commentText?: string;
  attachmentName?: string;
}

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
}: EditCommentProps) => {
  const dispatch = useAppDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const closeDialog = () => {
    setDialogOpen(false);
  };

  const editCommentOnObject = (
    sourceID: any,
    commentID: any,
    formData: any,
  ) => {
    formData.obj_id = sourceID;
    dispatch(sourceActions.editComment(commentID, formData));
  };

  const editCommentOnSpectrum = (
    spectrumID: any,
    commentID: any,
    formData: any,
  ) => {
    formData.spectrum_id = spectrumID;
    dispatch(sourceActions.editComment(commentID, formData));
  };

  const editCommentOnGcnEvent = (gcnID: any, commentID: any, formData: any) => {
    dispatch(gcnEventActions.editCommentOnGcnEvent(commentID, gcnID, formData));
  };

  const editCommentOnShift = (shift_id: any, commentID: any, formData: any) => {
    formData.shift_id = shift_id;
    dispatch(shiftsActions.editCommentOnShift(commentID, formData));
  };

  const editComment = (data: any) => {
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

export default EditComment;

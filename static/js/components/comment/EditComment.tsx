import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Button from "../Button";
import CommentEntry from "./CommentEntry";

import { useEditCommentMutation } from "../../ducks/source";
import { useEditCommentOnGcnEventMutation } from "../../ducks/gcnEvent";
import { useEditCommentOnShiftMutation } from "../../ducks/shifts";

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
  const [editCommentMutation] = useEditCommentMutation();
  const [editCommentOnShiftMutation] = useEditCommentOnShiftMutation();
  const [editCommentOnGcnEventMutation] = useEditCommentOnGcnEventMutation();

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
    editCommentMutation({ commentID, formData });
  };

  const editCommentOnSpectrum = (
    spectrumID: any,
    commentID: any,
    formData: any,
  ) => {
    formData.spectrum_id = spectrumID;
    editCommentMutation({ commentID, formData });
  };

  const editCommentOnGcnEvent = (gcnID: any, commentID: any, formData: any) => {
    editCommentOnGcnEventMutation({
      commentID,
      gcnEventID: gcnID,
      formData,
    });
  };

  const editCommentOnShift = (shift_id: any, commentID: any, formData: any) => {
    formData.shift_id = shift_id;
    editCommentOnShiftMutation({ commentID, formData });
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
      <Tooltip title="Edit">
        <IconButton
          size="small"
          type="button"
          name={`editCommentButton${id}`}
          onClick={() => setDialogOpen(true)}
          className="commentEdit"
          sx={{
            padding: "0.125rem",
            color: "text.secondary",
            visibility: hoverID === id ? "visible" : "hidden",
          }}
        >
          <EditIcon fontSize="inherit" />
        </IconButton>
      </Tooltip>
      <div>
        <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
          <DialogTitle>Edit comment</DialogTitle>
          <DialogContent dividers>
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
            <Button
              primary
              type="submit"
              form="edit-comment-form"
              name={`editCommentSubmitButton${id}`}
            >
              Edit
            </Button>
          </DialogActions>
        </Dialog>
      </div>
    </div>
  );
};

export default EditComment;

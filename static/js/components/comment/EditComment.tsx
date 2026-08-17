import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Button from "../Button";
import CommentForm from "./CommentForm";

import { useEditCommentMutation } from "../../ducks/source";
import { useEditCommentOnGcnEventMutation } from "../../ducks/gcnEvent";
import { useEditCommentOnShiftMutation } from "../../ducks/shifts";
import { useEditCommentOnEarthquakeMutation } from "../../ducks/earthquake";

interface EditCommentProps {
  resourceType?: string;
  objID?: string | null;
  gcnEventID?: string | number | null;
  earthquakeID?: string | null;
  spectrum_id?: string | null;
  id?: string | number | null;
  hoverID?: number | null;
  shiftID?: number | null;
  commentText?: string;
  attachmentName?: string;
}

const EditComment = ({
  resourceType = "sources",
  objID = null,
  gcnEventID = null,
  earthquakeID = null,
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
  const [editCommentOnEarthquakeMutation] =
    useEditCommentOnEarthquakeMutation();

  const [dialogOpen, setDialogOpen] = useState(false);
  const closeDialog = () => {
    setDialogOpen(false);
  };

  const editComment = (formData: any) => {
    switch (resourceType) {
      case "sources":
        formData.obj_id = objID;
        editCommentMutation({ commentID: id!, formData });
        break;
      case "spectra":
        formData.spectrum_id = spectrum_id;
        editCommentMutation({ commentID: id!, formData });
        break;
      case "gcn_event":
        editCommentOnGcnEventMutation({
          commentID: id!,
          gcnEventID: gcnEventID!,
          formData,
        });
        break;
      case "shift":
        formData.shift_id = shiftID;
        editCommentOnShiftMutation({ commentID: id!, formData });
        break;
      case "earthquake":
        editCommentOnEarthquakeMutation({
          commentID: id!,
          earthquakeID: earthquakeID!,
          formData,
        });
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
            <CommentForm
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

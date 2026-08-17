import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

import {
  useDeleteCommentMutation,
  useDeleteCommentOnSpectrumMutation,
} from "../../ducks/source";
import { useDeleteCommentOnGcnEventMutation } from "../../ducks/gcnEvent";
import { useDeleteCommentOnShiftMutation } from "../../ducks/shifts";
import { useDeleteCommentOnEarthquakeMutation } from "../../ducks/earthquake";

interface DeleteCommentProps {
  resourceType?: string;
  objID?: string | null;
  gcnEventID?: string | number | null;
  earthquakeID?: string | null;
  spectrum_id?: string | null;
  id?: string | number | null;
  hoverID?: number | null;
  shiftID?: number | null;
}

const DeleteComment = ({
  resourceType = "sources",
  objID = null,
  gcnEventID = null,
  earthquakeID = null,
  spectrum_id = null,
  id = null,
  hoverID = null,
  shiftID = null,
}: DeleteCommentProps) => {
  const [deleteComment] = useDeleteCommentMutation();
  const [deleteCommentOnSpectrum] = useDeleteCommentOnSpectrumMutation();
  const [deleteCommentOnShift] = useDeleteCommentOnShiftMutation();
  const [deleteCommentOnGcnEvent] = useDeleteCommentOnGcnEventMutation();
  const [deleteCommentOnEarthquake] = useDeleteCommentOnEarthquakeMutation();

  const onDelete = () => {
    const commentID = id!;
    switch (resourceType) {
      case "sources":
        deleteComment({ sourceID: objID!, commentID });
        break;
      case "spectra":
        deleteCommentOnSpectrum({ spectrumID: spectrum_id!, commentID });
        break;
      case "gcn_event":
        deleteCommentOnGcnEvent({ gcnEventID: gcnEventID!, commentID });
        break;
      case "shift":
        deleteCommentOnShift({ shiftID: shiftID!, commentID });
        break;
      case "earthquake":
        deleteCommentOnEarthquake({ earthquakeID: earthquakeID!, commentID });
        break;
      default:
        break;
    }
  };

  return (
    <Tooltip title="Delete">
      <IconButton
        size="small"
        type="button"
        name={`deleteCommentButton${id}`}
        onClick={onDelete}
        className="commentDelete"
        sx={{
          padding: "0.125rem",
          color: "text.secondary",
          visibility: hoverID === id ? "visible" : "hidden",
        }}
      >
        <CloseIcon fontSize="inherit" />
      </IconButton>
    </Tooltip>
  );
};

export default DeleteComment;

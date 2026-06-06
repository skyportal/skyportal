import CloseIcon from "@mui/icons-material/Close";
import Button from "../Button";

import {
  useDeleteCommentMutation,
  useDeleteCommentOnSpectrumMutation,
} from "../../ducks/source";
import { useDeleteCommentOnGcnEventMutation } from "../../ducks/gcnEvent";
import { useDeleteCommentOnShiftMutation } from "../../ducks/shifts";

interface DeleteCommentProps {
  associatedResourceType?: string;
  objID?: string | null;
  gcnEventID?: string | number | null;
  spectrum_id?: string | null;
  id?: string | number | null;
  hoverID?: number | null;
  shiftID?: number | null;
}

const DeleteComment = ({
  associatedResourceType = "object",
  objID = null,
  gcnEventID = null,
  spectrum_id = null,
  id = null,
  hoverID = null,
  shiftID = null,
}: DeleteCommentProps) => {
  const [deleteCommentMutation] = useDeleteCommentMutation();
  const [deleteCommentOnSpectrumMutation] =
    useDeleteCommentOnSpectrumMutation();
  const [deleteCommentOnShiftMutation] = useDeleteCommentOnShiftMutation();
  const [deleteCommentOnGcnEventMutation] =
    useDeleteCommentOnGcnEventMutation();
  const deleteCommentOnObject = (
    sourceID: string | null,
    commentID: string | number | null,
  ) => {
    deleteCommentMutation({ sourceID: sourceID!, commentID: commentID! });
  };

  const deleteCommentOnSpectrum = (
    commentSpectrumID: string | null,
    commentID: string | number | null,
  ) => {
    deleteCommentOnSpectrumMutation({
      spectrumID: commentSpectrumID!,
      commentID: commentID!,
    });
  };

  const deleteCommentOnGcnEvent = (
    gcnID: string | number | null,
    commentID: string | number | null,
  ) => {
    deleteCommentOnGcnEventMutation({
      gcnEventID: gcnID!,
      commentID: commentID!,
    });
  };

  const deleteCommentOnShift = (
    shift_id: number | null,
    commentID: string | number | null,
  ) => {
    deleteCommentOnShiftMutation({ shiftID: shift_id!, commentID: commentID! });
  };

  const deleteComment = (resourceType: string) => {
    switch (resourceType) {
      case "object":
        deleteCommentOnObject(objID, id);
        break;
      case "spectrum":
        deleteCommentOnSpectrum(spectrum_id, id);
        break;
      case "gcn_event":
        deleteCommentOnGcnEvent(gcnEventID, id);
        break;
      case "shift":
        deleteCommentOnShift(shiftID, id);
        break;
      default:
        break;
    }
  };

  return (
    <>
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
        name={`deleteCommentButton${id}`}
        onClick={() => deleteComment(associatedResourceType)}
        className="commentDelete"
      >
        <CloseIcon fontSize="small" />
      </Button>
    </>
  );
};

export default DeleteComment;

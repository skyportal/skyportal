import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { isMobile } from "react-device-detect";
import { Link as RouterLink } from "react-router-dom";

import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
import GroupIcon from "@mui/icons-material/Group";
import SmartToyIcon from "@mui/icons-material/SmartToy";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import { useFetchSourceSpectraQuery } from "../../ducks/spectra";
import {
  useEditCommentMutation,
  useDeleteCommentMutation,
  useDeleteCommentOnSpectrumMutation,
} from "../../ducks/source";
import {
  useEditCommentOnGcnEventMutation,
  useDeleteCommentOnGcnEventMutation,
} from "../../ducks/gcnEvent";
import {
  useEditCommentOnShiftMutation,
  useDeleteCommentOnShiftMutation,
} from "../../ducks/shifts";
import {
  useEditCommentOnEarthquakeMutation,
  useDeleteCommentOnEarthquakeMutation,
} from "../../ducks/earthquake";
import UserAvatar from "../user/UserAvatar";

import CommentAttachmentPreview from "./CommentAttachmentPreview";
import CommentForm from "./CommentForm";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const actionButtonStyle = {
  padding: "0.125rem",
  color: "text.secondary",
};

const LINK_REGEX = /(\[[^\]]*\]\([^)]*\)|<[^\s>]+>|(?:https?:\/\/|www\.)\S+)/g;
const MENTION_REGEX = /(?<!\w)([@#])([\w-@]+)/g;

const highlightMentions = (text: string) =>
  text
    .split(LINK_REGEX)
    .map((chunk, index) =>
      index % 2 ? chunk : chunk.replace(MENTION_REGEX, "***$1$2***"),
    )
    .join("");

const markdownLink = ({ node, children, ...props }: any) => (
  <Link
    {...props}
    target="_blank"
    rel="noopener noreferrer"
    onClick={(event: any) => event.stopPropagation()}
    sx={{ overflowWrap: "anywhere" }}
  >
    {children}
  </Link>
);

interface CommentProps {
  resourceType?: string;
  objID?: string | null;
  gcnEventID?: number | null;
  earthquakeID?: string | null;
  styles?: Record<string, any>;
  id?: any;
  author?: Record<string, any>;
  created_at?: string | null;
  text?: string | null;
  attachment_name?: string | null;
  groups?: { name: string; [key: string]: any }[];
  spectrum_id?: string | null;
  bot?: boolean;
  hoverID?: number | null;
  shiftID?: number | null;
}

const Comment = ({
  resourceType = "sources",
  objID = null,
  gcnEventID = null,
  earthquakeID = null,
  styles = {},
  id = null,
  author = {},
  created_at = null,
  text = null,
  attachment_name = null,
  groups = [],
  spectrum_id = null,
  bot = false,
  hoverID = null,
  shiftID = null,
}: CommentProps) => {
  const [editing, setEditing] = useState(false);
  const { data: spectra } = useFetchSourceSpectraQuery(
    { id: objID as string },
    { skip: !objID },
  );
  const [editCommentMutation] = useEditCommentMutation();
  const [editCommentOnGcnEvent] = useEditCommentOnGcnEventMutation();
  const [editCommentOnShift] = useEditCommentOnShiftMutation();
  const [editCommentOnEarthquake] = useEditCommentOnEarthquakeMutation();
  const [deleteCommentMutation] = useDeleteCommentMutation();
  const [deleteCommentOnSpectrum] = useDeleteCommentOnSpectrumMutation();
  const [deleteCommentOnGcnEvent] = useDeleteCommentOnGcnEventMutation();
  const [deleteCommentOnShift] = useDeleteCommentOnShiftMutation();
  const [deleteCommentOnEarthquake] = useDeleteCommentOnEarthquakeMutation();

  const showActions = (isMobile || hoverID === id) && !editing;

  const editComment = (formData: any) => {
    switch (resourceType) {
      case "sources":
        editCommentMutation({
          commentID: id,
          formData: { ...formData, obj_id: objID },
        });
        break;
      case "spectra":
        editCommentMutation({
          commentID: id,
          formData: { ...formData, spectrum_id },
        });
        break;
      case "gcn_event":
        editCommentOnGcnEvent({
          commentID: id,
          gcnEventID: gcnEventID!,
          formData,
        });
        break;
      case "shift":
        editCommentOnShift({
          commentID: id,
          formData: { ...formData, shift_id: shiftID },
        });
        break;
      case "earthquake":
        editCommentOnEarthquake({
          commentID: id,
          earthquakeID: earthquakeID!,
          formData,
        });
        break;
      default:
        break;
    }
  };

  const deleteComment = () => {
    switch (resourceType) {
      case "sources":
        deleteCommentMutation({ sourceID: objID!, commentID: id });
        break;
      case "spectra":
        deleteCommentOnSpectrum({ spectrumID: spectrum_id!, commentID: id });
        break;
      case "gcn_event":
        deleteCommentOnGcnEvent({ gcnEventID: gcnEventID!, commentID: id });
        break;
      case "shift":
        deleteCommentOnShift({ shiftID: shiftID!, commentID: id });
        break;
      case "earthquake":
        deleteCommentOnEarthquake({
          earthquakeID: earthquakeID!,
          commentID: id,
        });
        break;
      default:
        break;
    }
  };

  const renderCommentText = () => {
    const formattedText = highlightMentions(text ?? "");

    if (spectrum_id && objID && spectra && resourceType === "sources") {
      const spectrum = spectra.find((spec: any) => spec.id === spectrum_id);
      if (!spectrum) {
        return formattedText;
      }
      const dayFraction =
        (parseFloat(spectrum.observed_at.substring(11, 13)) / 24) * 10;
      return `**Spectrum ${spectrum.observed_at.substring(
        2,
        10,
      )}.${dayFraction.toFixed(0)}** ${formattedText}`;
    }

    return formattedText;
  };

  const emojiSupport = (textComment: any) =>
    textComment.value.replace(/:\w+:/gi, (name: string) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name,
    );

  const commentMessageStyle =
    resourceType === "shift"
      ? styles["commentMessageShift"]
      : styles["commentMessage"];

  return (
    <>
      <div className={styles["commentUserAvatar"]}>
        <UserAvatar
          size={24}
          userId={author["id"]}
          firstName={author["first_name"]}
          lastName={author["last_name"]}
          username={author["username"]}
          gravatarUrl={author["gravatar_url"]}
          isBot={author?.["is_bot"] || false}
        />
      </div>
      <div className={styles["commentContent"]}>
        <div className={styles["commentHeader"]}>
          <div className={styles["commentHeaderContent"]}>
            <span className={styles["commentUser"]}>
              <span className={styles["commentUserName"]}>
                {bot ? (
                  <>
                    <SmartToyIcon fontSize="inherit" />
                    Bot message ({author["username"]})
                  </>
                ) : author["id"] ? (
                  <Link
                    component={RouterLink}
                    to={`/user/${author["id"]}`}
                    underline="hover"
                    sx={{ color: "inherit" }}
                  >
                    {author["username"]}
                  </Link>
                ) : (
                  author["username"]
                )}
              </span>
            </span>
            <span className={styles["commentTime"]}>
              {dayjs().to(dayjs.utc(`${created_at}Z`))}
            </span>
            <span className={styles["commentUserGroup"]}>
              <Tooltip title={groups?.map((group) => group.name)?.join(", ")}>
                <GroupIcon fontSize="small" viewBox="0 -2 24 24" />
              </Tooltip>
            </span>
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-end",
              alignItems: "center",
              gap: "0.25rem",
              width: "30%",
              visibility: showActions ? "visible" : "hidden",
            }}
          >
            <Tooltip title="Edit">
              <IconButton
                size="small"
                name={`editCommentButton${id}`}
                onClick={() => setEditing(true)}
                sx={actionButtonStyle}
              >
                <EditIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton
                size="small"
                name={`deleteCommentButton${id}`}
                onClick={deleteComment}
                className="commentDelete"
                sx={actionButtonStyle}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
          </div>
        </div>
        {editing ? (
          <>
            <CommentForm
              editComment={editComment}
              commentText={text ?? ""}
              attachmentName={attachment_name ?? ""}
              onClose={() => setEditing(false)}
            />
            <Typography variant="caption" color="text.secondary">
              Enter to save, Escape to cancel
            </Typography>
          </>
        ) : (
          <div
            className={styles["wrap"]}
            {...({
              name: `commentDiv${(spectrum_id ? "Spectrum" : "Source") + id}`,
            } as any)}
          >
            <ReactMarkdown
              className={commentMessageStyle}
              remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
              components={{ text: emojiSupport, a: markdownLink }}
            >
              {renderCommentText()}
            </ReactMarkdown>
          </div>
        )}
        <span>
          {attachment_name &&
            (resourceType === "sources" || resourceType === "spectra") && (
              <CommentAttachmentPreview
                filename={attachment_name}
                objectID={spectrum_id || objID}
                commentId={id}
                resourceType={spectrum_id ? "spectra" : "sources"}
              />
            )}
          {attachment_name && resourceType === "gcn_event" && (
            <CommentAttachmentPreview
              filename={attachment_name}
              gcnEventID={gcnEventID}
              commentId={id}
              resourceType="gcn_event"
            />
          )}
          {attachment_name && resourceType === "shift" && (
            <CommentAttachmentPreview
              filename={attachment_name}
              shiftID={shiftID}
              commentId={id}
              resourceType="shift"
            />
          )}
          {attachment_name && resourceType === "earthquake" && (
            <CommentAttachmentPreview
              filename={attachment_name}
              earthquakeID={earthquakeID}
              commentId={id}
              resourceType="earthquake"
            />
          )}
        </span>
      </div>
    </>
  );
};

export default Comment;

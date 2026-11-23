import { useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { isMobile } from "react-device-detect";
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
import GroupIcon from "@mui/icons-material/Group";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

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
import { useGetConfigQuery } from "../../ducks/config";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetStreamsQuery } from "../../ducks/streams";
import UserAvatar from "../user/UserAvatar";

import CommentAttachmentPreview from "./CommentAttachmentPreview";
import { bubbleSx } from "./chatStyles";
import CommentForm from "./CommentForm";
import { rehypeEmoji } from "./rehypeEmoji";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const actionButtonSx = {
  padding: "0.2rem",
  color: "text.secondary",
};

const LINK_REGEX = /(\[[^\]]*\]\([^)]*\)|<[^\s>]+>|(?:https?:\/\/|www\.)\S+)/g;
const MENTION_REGEX = /(?<!\w)([@#])([\w-@]+)/g;

export const highlightMentions = (text: string) =>
  text
    .split(LINK_REGEX)
    .map((chunk, index) =>
      index % 2 ? chunk : chunk.replace(MENTION_REGEX, "***$1$2***"),
    )
    .join("");

export const markdownLink = ({ node, children, ...props }: any) => (
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
  id?: any;
  author?: Record<string, any>;
  created_at?: string | null;
  text?: string | null;
  attachment_name?: string | null;
  groups?: { name: string; [key: string]: any }[];
  stream_ids?: number[] | null;
  hidden_stream_ids?: number[] | null;
  spectrum_id?: string | null;
  bot?: boolean;
  hoverID?: number | null;
  shiftID?: number | null;
  compact?: boolean;
  versionSwitch?: ReactNode;
}

const Comment = ({
  resourceType = "sources",
  objID = null,
  gcnEventID = null,
  earthquakeID = null,
  id = null,
  author = {},
  created_at = null,
  text = null,
  attachment_name = null,
  groups = [],
  stream_ids = null,
  hidden_stream_ids = null,
  spectrum_id = null,
  bot = false,
  hoverID = null,
  shiftID = null,
  compact = false,
  versionSwitch = null,
}: CommentProps) => {
  const [editing, setEditing] = useState(false);
  const { data: streams } = useGetStreamsQuery(undefined, {
    skip: !stream_ids?.length && !hidden_stream_ids?.length,
  });
  const config = useGetConfigQuery().data as any;
  const myId = useGetProfileQuery().data?.id;
  const mine = author["id"] != null && author["id"] === myId;
  const { data: spectra } = useFetchSourceSpectraQuery(
    { id: objID as string },
    { skip: !objID || !spectrum_id },
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

  const streamNames = (ids: number[]) =>
    ids
      .map(
        (streamID) =>
          streams?.find((stream) => stream.id === streamID)?.name ??
          `stream ${streamID}`,
      )
      .join(", ");

  const visibility = [
    groups?.some((group) => group.name === config?.publicGroupName)
      ? null
      : groups?.map((group) => group.name)?.join(", "),
    stream_ids?.length ? `Visible to ${streamNames(stream_ids)}` : null,
    hidden_stream_ids?.length
      ? `Visible to users without ${streamNames(hidden_stream_ids)}`
      : null,
  ].filter(Boolean) as string[];

  const avatar = (
    <UserAvatar
      size={compact ? 18 : 28}
      userId={author["id"]}
      firstName={author["first_name"]}
      lastName={author["last_name"]}
      username={author["username"]}
      gravatarUrl={author["gravatar_url"]}
      isBot={author?.["is_bot"] || false}
    />
  );

  return (
    <>
      {!compact && (
        <Box sx={{ flexShrink: 0, paddingTop: "0.125rem" }}>{avatar}</Box>
      )}
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: "0.2rem",
          flex: 1,
          minWidth: 0,
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            alignSelf: "stretch",
            minHeight: "1.5rem",
          }}
        >
          {compact && avatar}
          <Box
            component="span"
            sx={{
              fontSize: "0.8rem",
              fontWeight: 600,
              whiteSpace: "nowrap",
              color: bot ? "text.secondary" : "text.primary",
            }}
          >
            {bot ? (
              `Bot message (${author["username"]})`
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
          </Box>
          <Box
            component="span"
            sx={{
              fontSize: "0.75rem",
              color: "text.secondary",
              whiteSpace: "nowrap",
            }}
          >
            {dayjs().to(dayjs.utc(`${created_at}Z`))}
          </Box>
          {visibility.length > 0 && (
            <Tooltip
              title={visibility.map((line) => (
                <div key={line}>{line}</div>
              ))}
            >
              <GroupIcon sx={{ fontSize: "1rem", color: "text.secondary" }} />
            </Tooltip>
          )}
          {versionSwitch}
          <Box
            sx={{
              display: "flex",
              gap: "0.125rem",
              marginLeft: "auto",
              visibility: showActions ? "visible" : "hidden",
            }}
          >
            <Tooltip title="Edit">
              <IconButton
                size="small"
                name={`editCommentButton${id}`}
                onClick={() => setEditing(true)}
                sx={actionButtonSx}
              >
                <EditIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete">
              <IconButton
                size="small"
                name={`deleteCommentButton${id}`}
                onClick={deleteComment}
                sx={{ ...actionButtonSx, "&:hover": { color: "error.main" } }}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        {editing ? (
          <Box sx={{ alignSelf: "stretch" }}>
            <CommentForm
              editComment={editComment}
              commentText={text ?? ""}
              attachmentName={attachment_name ?? ""}
              onClose={() => setEditing(false)}
            />
            <Typography variant="caption" color="text.secondary">
              Enter to save, Escape to cancel
            </Typography>
          </Box>
        ) : (
          <Box
            {...({
              name: `commentDiv${(spectrum_id ? "Spectrum" : "Source") + id}`,
            } as any)}
            sx={(theme) => ({
              maxWidth: "min(100%, 40rem)",
              fontSize: bot ? "0.8rem" : "0.875rem",
              lineHeight: 1.5,
              overflowWrap: "anywhere",
              color: bot ? "text.secondary" : "text.primary",
              "& p": { margin: 0 },
              "& p + p": { marginTop: "0.4em" },
              "& pre": { whiteSpace: "pre-wrap" },
              ...(!bot && bubbleSx(theme, mine)),
            })}
          >
            <ReactMarkdown
              className="commentMessage"
              remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
              rehypePlugins={[rehypeEmoji]}
              components={{ a: markdownLink }}
            >
              {renderCommentText()}
            </ReactMarkdown>
          </Box>
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
      </Box>
    </>
  );
};

export default Comment;

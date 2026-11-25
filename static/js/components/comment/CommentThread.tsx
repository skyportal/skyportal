import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useRef, useState } from "react";

import type { Theme } from "@mui/material/styles";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Skeleton from "@mui/material/Skeleton";
import Tooltip from "@mui/material/Tooltip";

import ReactMarkdown from "react-markdown";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { skipToken } from "@reduxjs/toolkit/query";

import {
  useGetSourceQuery,
  useAddCommentMutation,
  useGetConversationQuery,
} from "../../ducks/source";
import { useFetchSourceSpectraQuery } from "../../ducks/spectra";
import { useGetCandidateQuery } from "../../ducks/candidate/candidate";
import {
  useGetGcnEventQuery,
  useAddCommentOnGcnEventMutation,
} from "../../ducks/gcnEvent";
import {
  useAddCommentOnShiftMutation,
  useGetShiftQuery,
} from "../../ducks/shifts";
import {
  useGetEarthquakeQuery,
  useAddCommentOnEarthquakeMutation,
} from "../../ducks/earthquake";
import SegmentedControl from "../SegmentedControl";

import CommentForm from "./CommentForm";
import Comment from "./Comment";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const systemCommentSx = (theme: Theme) => ({
  textAlign: "center",
  color: theme.palette.text.secondary,
  fontSize: "0.75rem",
  padding: "0.4rem 0.5rem",
  "& > p": { margin: 0 },
  "& strong": { color: theme.palette.text.primary },
  "& strong:first-of-type": { color: theme.palette.primary.main },
});

interface CommentThreadProps {
  isCandidate?: boolean;
  objID?: string | null;
  gcnEventID?: number | null;
  gcnEventDateobs?: string | null;
  earthquakeID?: string | null;
  earthquakeEventID?: string | null;
  resourceType?: string;
  spectrumID?: number | null;
  shiftID?: number | null;
  includeCommentsOnAllResourceTypes?: boolean;
  // Omit to let the list fill the height its parent gives it.
  maxHeightList?: string;
  channel?: string | undefined;
  origin?: "scanning" | undefined;
  pinned?: boolean;
  compact?: boolean;
}

const CommentThread = ({
  isCandidate = false,
  resourceType = "sources",
  objID = null,
  spectrumID = null,
  gcnEventID = null,
  gcnEventDateobs = null,
  earthquakeID = null,
  earthquakeEventID = null,
  shiftID = null,
  includeCommentsOnAllResourceTypes = true,
  maxHeightList,
  channel,
  origin,
  pinned = false,
  compact = false,
}: CommentThreadProps) => {
  const [hoverID, setHoverID] = useState<any>(null);

  const handleMouseHover = (id: any, userProfile: any, author: any) => {
    if (
      userProfile.permissions.includes("System admin") ||
      userProfile.username === author
    ) {
      setHoverID(id);
    }
  };

  const handleMouseLeave = () => {
    setHoverID(null);
  };

  const [addCommentMutation] = useAddCommentMutation();
  const { data: candidate } = useGetCandidateQuery(
    isCandidate && objID ? objID : skipToken,
  );
  const { data: source } = useGetSourceQuery(
    !isCandidate && objID ? objID : skipToken,
  );
  const { data: conversation } = useGetConversationQuery(
    objID && channel ? { obj_id: objID, channel } : skipToken,
  );
  const obj: any = isCandidate ? candidate : source;
  const resolvedObjID = objID ?? obj?.id ?? null;
  const { data: spectra } = useFetchSourceSpectraQuery(
    { id: resolvedObjID as string },
    {
      skip:
        !resolvedObjID ||
        (resourceType === "sources" && !includeCommentsOnAllResourceTypes),
    },
  );
  const { data: gcnEvent } = useGetGcnEventQuery(
    gcnEventDateobs ?? skipToken,
  ) as { data: any };
  const [addCommentOnGcnEvent] = useAddCommentOnGcnEventMutation();
  const { data: earthquake } = useGetEarthquakeQuery(
    earthquakeEventID ?? skipToken,
  ) as { data: any };
  const { data: userProfile } = useGetProfileQuery();
  const permissions = useGetProfileQuery().data?.permissions;
  const [addCommentOnShift] = useAddCommentOnShiftMutation();
  const { data: currentShift } = useGetShiftQuery(shiftID ?? skipToken) as {
    data: any;
  };
  const [addCommentOnEarthquake] = useAddCommentOnEarthquakeMutation();
  const showBotComments = (useGetProfileQuery().data?.preferences as any)
    ?.showBotComments;

  const [includeBots, setIncludeBots] = useState(false);
  const [publicShown, setPublicShown] = useState<number[]>([]);

  useEffect(() => {
    setIncludeBots(showBotComments);
  }, [showBotComments]);

  if (!objID && obj) {
    objID = obj.id;
  }

  if (!gcnEventID && gcnEvent) {
    gcnEventID = gcnEvent.id;
  }

  if (!earthquakeID && earthquake) {
    earthquakeID = earthquake.id;
  }

  const resourceID: Record<string, any> = {
    sources: objID,
    spectra: objID,
    gcn_event: gcnEventID,
    shift: shiftID,
    earthquake: earthquakeID,
  };

  const addComment = (formData: any) => {
    switch (resourceType) {
      case "sources":
      case "spectra":
        return addCommentMutation({
          obj_id: objID,
          spectrum_id: spectrumID,
          channel,
          ...formData,
          origin,
        });
      case "gcn_event":
        return addCommentOnGcnEvent({ gcnevent_id: gcnEventID, ...formData });
      case "shift":
        return addCommentOnShift({ shiftID, ...formData });
      case "earthquake":
        return addCommentOnEarthquake({
          earthquake_id: earthquakeID,
          ...formData,
        });
      default:
        return undefined;
    }
  };

  let comments: any = null;
  let specComments: any = null;

  if (resourceType === "sources") {
    comments = channel ? conversation : obj?.comments;
    if (
      !channel &&
      includeCommentsOnAllResourceTypes &&
      Array.isArray(spectra) &&
      objID != null
    ) {
      specComments = spectra
        .map((spec: any) => spec.comments || [])
        .flat()
        .filter(Boolean);
    }
    if (comments !== null && specComments !== null) {
      comments = specComments.concat(comments);
      comments.sort((a: any, b: any) => (a.created_at < b.created_at ? 1 : -1));
    }
  } else if (resourceType === "spectra") {
    if (spectrumID === null) {
      throw new Error("Must specify a spectrumID for comments on spectra");
    }
    const spectrum = spectra?.find((spec: any) => spec.id === spectrumID);
    comments = spectrum?.comments;
  } else if (resourceType === "gcn_event") {
    if (gcnEventID === null) {
      throw new Error("Must specify a gcnEventID for comments on gcnEvent");
    }
    comments = gcnEvent?.comments;
  } else if (resourceType === "shift") {
    if (shiftID === null) {
      throw new Error("Must specify a shiftID for comments on shift");
    }
    comments = currentShift?.comments;
  } else if (resourceType === "earthquake") {
    if (earthquakeID === null) {
      throw new Error(
        "Must specify an earthquakeID for comments on earthquake",
      );
    }
    comments = earthquake?.comments;
  } else {
    throw new Error(`Illegal input ${resourceType} to CommentThread. `);
  }

  const loading = comments == null;
  comments = (comments || []).filter(Boolean);

  if (!includeBots && !channel) {
    comments = comments?.filter((comment: any) => comment.bot === false);
  }

  comments = [...comments].sort((a: any, b: any) =>
    a.created_at < b.created_at ? -1 : 1,
  );

  const publicVersions: Record<number, any> = {};
  comments.forEach((comment: any) => {
    if (
      comment.private_version_id &&
      comments.some(
        (other: any) =>
          other.id === comment.private_version_id && !other.spectrum_id,
      )
    ) {
      publicVersions[comment.private_version_id] = comment;
    }
  });
  comments = comments
    .filter(
      (comment: any) =>
        !comment.private_version_id ||
        publicVersions[comment.private_version_id] !== comment,
    )
    .map((comment: any) =>
      !publicVersions[comment.id]
        ? comment
        : {
            ...(publicShown.includes(comment.id)
              ? publicVersions[comment.id]
              : comment),
            pairID: comment.id,
          },
    );

  const versionSwitch = (pairID: number) => (
    <SegmentedControl
      size="small"
      value={publicShown.includes(pairID) ? "public" : "private"}
      options={[
        { value: "private", label: "Private" },
        { value: "public", label: "Public" },
      ]}
      onChange={(version) =>
        setPublicShown(
          version === "public"
            ? [...publicShown, pairID]
            : publicShown.filter((id) => id !== pairID),
        )
      }
    />
  );

  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [channel, comments.length]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      <Box
        ref={listRef}
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: "0.125rem",
          flexGrow: 1,
          minHeight: 0,
          maxHeight: maxHeightList,
          overflowY: "auto",
          padding: "0.5rem 0.5rem 0.25rem",
        }}
      >
        {loading &&
          [0, 1, 2].map((i) => (
            <Box key={i} sx={{ display: "flex", gap: 1, p: 1 }}>
              <Skeleton variant="circular" width={24} height={24} />
              <Box sx={{ flex: 1 }}>
                <Skeleton width="30%" />
                <Skeleton width="80%" />
              </Box>
            </Box>
          ))}
        {!loading && comments.length === 0 && (
          <Box
            sx={{
              padding: "1.5rem 0.5rem",
              textAlign: "center",
              fontSize: "0.8rem",
              color: "text.secondary",
            }}
          >
            {channel && !pinned
              ? "This conversation is only kept once a message is sent."
              : "No comment yet."}
          </Box>
        )}
        {comments?.map(
          ({
            id,
            author,
            created_at,
            text,
            attachment_name,
            groups,
            stream_ids,
            hidden_stream_ids,
            spectrum_id,
            resourceType: commentResourceType,
            obj_id,
            bot,
            system,
            pairID,
          }: any) =>
            system ? (
              <Box key={`system${id}`} sx={systemCommentSx}>
                <ReactMarkdown>{text}</ReactMarkdown>
              </Box>
            ) : (
              <Box
                id="comment"
                key={(spectrum_id ? "Spectrum" : "Source") + id}
                sx={{
                  display: "flex",
                  gap: "0.625rem",
                  padding: "0.375rem 0.25rem",
                }}
                onMouseOver={() =>
                  handleMouseHover(id, userProfile, author.username)
                }
                onMouseOut={() => handleMouseLeave()}
                onFocus={() =>
                  handleMouseHover(id, userProfile, author.username)
                }
                onBlur={() => handleMouseLeave()}
              >
                {/* Meta-object provenance: comment aggregated from a linked source */}
                {obj_id && objID && obj_id !== objID && (
                  <Tooltip title={`From linked source ${obj_id}`}>
                    <Chip
                      label={obj_id}
                      size="small"
                      variant="outlined"
                      component="a"
                      href={`/source/${obj_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      clickable
                      sx={{ height: 18 }}
                    />
                  </Tooltip>
                )}
                <Comment
                  // Spectra comments are merged into the source thread, so the
                  // type comes from the comment itself when the API sends it.
                  resourceType={
                    commentResourceType ??
                    (spectrum_id ? "spectra" : resourceType)
                  }
                  bot={bot}
                  compact={compact}
                  id={id}
                  objID={objID}
                  gcnEventID={gcnEventID}
                  earthquakeID={earthquakeID}
                  author={author}
                  created_at={created_at}
                  text={text}
                  attachment_name={attachment_name}
                  groups={groups}
                  stream_ids={stream_ids}
                  hidden_stream_ids={hidden_stream_ids}
                  spectrum_id={spectrum_id}
                  hoverID={hoverID}
                  shiftID={shiftID}
                  versionSwitch={pairID ? versionSwitch(pairID) : null}
                />
              </Box>
            ),
        )}
      </Box>
      {!channel && !compact && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "flex-end",
            padding: "0 0.75rem",
            "& .MuiFormControlLabel-root": { margin: 0, gap: "0.25rem" },
            "& .MuiCheckbox-root": { padding: "0.125rem" },
          }}
        >
          <FormControlLabel
            label={
              <Box
                component="span"
                sx={{ fontSize: "0.75rem", color: "text.secondary" }}
              >
                Include bots
              </Box>
            }
            control={
              <Checkbox
                color="primary"
                size="small"
                onChange={(event) => setIncludeBots(event.target.checked)}
                checked={includeBots || false}
                {...({ title: "Include Bots?", type: "checkbox" } as any)}
              />
            }
          />
        </Box>
      )}
      {permissions?.includes("Comment") && resourceID[resourceType] && (
        <CommentForm
          addComment={addComment}
          streamAccess={resourceType === "sources"}
        />
      )}
    </Box>
  );
};

export default CommentThread;

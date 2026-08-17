import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useRef, useState } from "react";

import { makeStyles } from "tss-react/mui";
import { alpha } from "@mui/material/styles";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

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

import CommentForm from "./CommentForm";
import Comment from "./Comment";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  panelContainer: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    minHeight: 0,
  },
  panelList: {
    flexGrow: 1,
    minHeight: 0,
    overflowY: "auto",
    padding: "0.5rem 0.5rem 0",
  },
  panelBots: {
    display: "flex",
    justifyContent: "flex-end",
    padding: "0 0.5rem",
    "& .MuiFormControlLabel-root": {
      margin: 0,
    },
    "& .MuiCheckbox-root": {
      padding: "0.125rem",
    },
  },
  panelEmpty: {
    padding: "0.5rem",
    textAlign: "center",
    fontSize: "0.75rem",
    fontStyle: "italic",
    color: theme.palette.text.secondary,
  },
  panelBotsLabel: {
    fontSize: "0.7rem",
    color: theme.palette.text.secondary,
  },
  botComment: {
    fontSize: "80%",
    color: theme.palette.text.secondary,
    backgroundColor: alpha(theme.palette.text.primary, 0.05),
    "&:hover": {
      backgroundColor: alpha(theme.palette.text.primary, 0.09),
    },
  },
  botUserName: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.25em",
    color: theme.palette.text.secondary,
    fontWeight: 500,
  },
  comment: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: "#e0e0e0",
    },
    "& .commentDelete": {
      "&:hover": {
        color: "#e63946",
      },
    },
  },
  commentDark: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: "#3a3a3a",
    },
    "& .commentDelete": {
      color: "#b1dae9",
      "&:hover": {
        color: "#e63946",
      },
    },
  },
  commentContent: {
    display: "flex",
    flexFlow: "column nowrap",
    padding: "0.3125rem 0.625rem 0.3125rem 0.875rem",
    borderRadius: "15px",
    width: "100%",
  },
  commentHeader: {
    display: "flex",
    alignItems: "center",
  },
  commentHeaderContent: {
    width: "70%",
  },
  commentTime: {
    color: "gray",
    fontSize: "80%",
    marginRight: "1em",
  },
  commentMessage: {
    maxWidth: "35em",
    "& > p": {
      margin: "0",
    },
    wordWrap: "break-word",
  },
  commentMessageShift: {
    maxWidth: "47em",
    "& > p": {
      margin: "0",
    },
    wordWrap: "break-word",
  },
  commentUserName: {
    fontWeight: "bold",
    fontSize: "90%",
    marginRight: "0.5em",
    whiteSpace: "nowrap",
    color: "#76aace",
  },
  commentUserAvatar: {
    display: "block",
    margin: "0.5em",
  },
  commentUserGroup: {
    display: "inline-block",
    "& > svg": {
      fontSize: "1rem",
    },
  },
  wrap: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: "27px",
    maxWidth: "25em",
  },
}));

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
}: CommentThreadProps) => {
  const { classes: styles, cx } = useStyles();
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
    { skip: !resolvedObjID },
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
  const userColorTheme = (useGetProfileQuery().data?.preferences as any)?.theme;

  const [includeBots, setIncludeBots] = useState(false);

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
        addCommentMutation({
          obj_id: objID,
          spectrum_id: spectrumID,
          channel,
          ...formData,
        });
        break;
      case "gcn_event":
        addCommentOnGcnEvent({ gcnevent_id: gcnEventID, ...formData });
        break;
      case "shift":
        addCommentOnShift({ shiftID, ...formData });
        break;
      case "earthquake":
        addCommentOnEarthquake({ earthquake_id: earthquakeID, ...formData });
        break;
      default:
        break;
    }
  };

  let comments: any = null;
  let specComments: any = null;

  if (resourceType === "sources") {
    comments = channel ? (conversation ?? []) : obj?.comments;
    if (
      includeCommentsOnAllResourceTypes &&
      Array.isArray(spectra) &&
      objID != null
    ) {
      specComments = spectra?.map((spec: any) => spec.comments)?.flat();
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

  comments = comments || [];

  if (!includeBots && !channel) {
    comments = comments?.filter((comment: any) => comment.bot === false);
  }

  comments = [...comments].sort((a: any, b: any) =>
    a.created_at < b.created_at ? -1 : 1,
  );

  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  const botStyles = {
    ...styles,
    commentUserName: cx(styles.commentUserName, styles.botUserName),
  };

  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [channel, comments.length]);

  return (
    <div className={styles.panelContainer}>
      <div
        ref={listRef}
        className={styles.panelList}
        style={{ maxHeight: maxHeightList }}
      >
        {comments.length === 0 && (
          <div className={styles.panelEmpty}>
            {channel
              ? "This conversation is only kept once a message is sent."
              : "No comment yet."}
          </div>
        )}
        {comments?.map(
          ({
            id,
            author,
            created_at,
            text,
            attachment_name,
            groups,
            spectrum_id,
            resourceType: commentResourceType,
            obj_id,
            bot,
          }: any) => (
            <span
              id="comment"
              key={(spectrum_id ? "Spectrum" : "Source") + id}
              className={cx(commentStyle, bot && styles.botComment)}
              onMouseOver={() =>
                handleMouseHover(id, userProfile, author.username)
              }
              onMouseOut={() => handleMouseLeave()}
              onFocus={() => handleMouseHover(id, userProfile, author.username)}
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
                    style={{ height: "18px", marginBottom: "0.2em" }}
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
                styles={bot ? botStyles : styles}
                id={id}
                objID={objID}
                gcnEventID={gcnEventID}
                earthquakeID={earthquakeID}
                author={author}
                created_at={created_at}
                text={text}
                attachment_name={attachment_name}
                groups={groups}
                spectrum_id={spectrum_id}
                hoverID={hoverID}
                shiftID={shiftID}
              />
            </span>
          ),
        )}
      </div>
      {!channel && (
        <div className={styles.panelBots}>
          <FormControlLabel
            label={<span className={styles.panelBotsLabel}>Include bots</span>}
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
        </div>
      )}
      {permissions?.includes("Comment") && resourceID[resourceType] && (
        <CommentForm addComment={addComment} />
      )}
    </div>
  );
};

export default CommentThread;

import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useState } from "react";

import { makeStyles } from "tss-react/mui";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { skipToken } from "@reduxjs/toolkit/query";

import { useGetSourceQuery, useAddCommentMutation } from "../../ducks/source";
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

import CommentEntry from "./CommentEntry";
import Comment from "./Comment";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  commentsContainer: {
    width: "100%",
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
  spacer: {
    width: "20px",
    padding: "0 10px",
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
  compactCommentMessage: {
    maxWidth: "34em",
    "& > p": {
      margin: "0",
    },
    wordWrap: "break-word",
  },
  compactCommentMessageShift: {
    maxWidth: "44em",
    "& > p": {
      margin: "0",
    },
    wordWrap: "break-word",
  },
  commentUserName: {
    fontWeight: "bold",
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
  compactContainer: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: "25px",
    margin: "0 15px",
    width: "100%",
  },
  compactWrap: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    padding: "0 5px",
  },
  compactButtons: {
    display: "flex",
    alignItems: "center",
  },
}));

interface CommentListProps {
  isCandidate?: boolean;
  objID?: string | null;
  gcnEventID?: number | null;
  gcnEventDateobs?: string | null;
  earthquakeID?: string | null;
  earthquakeEventID?: string | null;
  associatedResourceType?: string;
  spectrumID?: number | null;
  shiftID?: number | null;
  includeCommentsOnAllResourceTypes?: boolean;
  maxHeightList?: string;
}

const CommentList = ({
  isCandidate = false,
  associatedResourceType = "object",
  objID = null,
  spectrumID = null,
  gcnEventID = null,
  gcnEventDateobs = null,
  earthquakeID = null,
  earthquakeEventID = null,
  shiftID = null,
  includeCommentsOnAllResourceTypes = true,
  maxHeightList = "350px",
}: CommentListProps) => {
  const { classes: styles } = useStyles();
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

  const addComment = (formData: any) => {
    addCommentMutation({
      obj_id: objID,
      spectrum_id: spectrumID,
      ...formData,
    });
  };

  const addGcnEventComment = (formData: any) => {
    addCommentOnGcnEvent({
      gcnevent_id: gcnEventID,
      ...formData,
    });
  };

  const addEarthquakeComment = (formData: any) => {
    addCommentOnEarthquake({
      earthquake_id: earthquakeID,
      ...formData,
    });
  };

  const addShiftComment = (formData: any) => {
    addCommentOnShift({
      shiftID,
      ...formData,
    });
  };

  let comments: any = null;
  let specComments: any = null;

  if (associatedResourceType === "object") {
    comments = obj?.comments;
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
  } else if (associatedResourceType === "spectra") {
    if (spectrumID === null) {
      throw new Error("Must specify a spectrumID for comments on spectra");
    }
    const spectrum = spectra?.find((spec: any) => spec.id === spectrumID);
    comments = spectrum?.comments;
  } else if (associatedResourceType === "gcn_event") {
    if (gcnEventID === null) {
      throw new Error("Must specify a gcnEventID for comments on gcnEvent");
    }
    comments = gcnEvent?.comments;
  } else if (associatedResourceType === "shift") {
    if (shiftID === null) {
      throw new Error("Must specify a shiftID for comments on shift");
    }
    comments = currentShift?.comments;
  } else if (associatedResourceType === "earthquake") {
    if (earthquakeID === null) {
      throw new Error(
        "Must specify an earthquakeID for comments on earthquake",
      );
    }
    comments = earthquake?.comments;
  } else {
    throw new Error(`Illegal input ${associatedResourceType} to CommentList. `);
  }

  comments = comments || [];

  if (!includeBots) {
    comments = comments?.filter((comment: any) => comment.bot === false);
  }

  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  return (
    <div className={styles.commentsContainer}>
      <div
        style={{
          marginTop: "1rem",
          overflowY: "scroll",
          maxHeight: maxHeightList,
        }}
      >
        {comments?.map(
          ({
            id,
            author,
            created_at,
            text,
            attachment_name,
            groups,
            spectrum_id,
            resourceType,
            obj_id,
          }: any) => (
            <span
              id="comment"
              key={(spectrum_id ? "Spectrum" : "Source") + id}
              className={commentStyle}
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
                associatedResourceType={resourceType}
                styles={styles}
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
      <div>
        <FormControlLabel
          label="Include Bots?"
          control={
            <Checkbox
              color="primary"
              onChange={(event) => setIncludeBots(event.target.checked)}
              checked={includeBots || false}
              {...({ title: "Include Bots?", type: "checkbox" } as any)}
            />
          }
        />
      </div>
      {(permissions?.indexOf("Comment") ?? -1) >= 0 &&
        objID &&
        (associatedResourceType === "object" ||
          associatedResourceType === "spectra") && (
          <CommentEntry addComment={addComment} />
        )}
      {(permissions?.indexOf("Comment") ?? -1) >= 0 &&
        gcnEventID &&
        associatedResourceType === "gcn_event" && (
          <CommentEntry addComment={addGcnEventComment} />
        )}
      {(permissions?.indexOf("Comment") ?? -1) >= 0 &&
        shiftID &&
        associatedResourceType === "shift" && (
          <CommentEntry addComment={addShiftComment} />
        )}
      {(permissions?.indexOf("Comment") ?? -1) >= 0 &&
        earthquakeID &&
        associatedResourceType === "earthquake" && (
          <CommentEntry addComment={addEarthquakeComment} />
        )}
    </div>
  );
};

export default CommentList;

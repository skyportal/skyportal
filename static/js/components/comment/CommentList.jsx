import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import PropTypes from "prop-types";

import makeStyles from "@mui/styles/makeStyles";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as sourceActions from "../../ducks/source";
import * as gcnEventActions from "../../ducks/gcnEvent";
import * as shiftActions from "../../ducks/shift";
import * as earthquakeActions from "../../ducks/earthquake";

import CommentEntry from "./CommentEntry";
import CompactCommentList from "../CompactCommentList";
import RegularCommentList from "../RegularCommentList";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
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
  commentUserDomain: {
    color: "lightgray",
    fontSize: "80%",
    paddingRight: "0.5em",
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
  defaultCommentDelete: {
    display: "flex",
    justifyContent: "end",
    width: "30%",
  },
}));

const CommentList = ({
  isCandidate = false,
  associatedResourceType = "object",
  objID = null,
  spectrumID = null,
  gcnEventID = null,
  earthquakeID = null,
  shiftID = null,
  includeCommentsOnAllResourceTypes = true,
  maxHeightList = "350px",
}) => {
  const styles = useStyles({ maxHeightList });
  const [hoverID, setHoverID] = useState(null);

  const handleMouseHover = (id, userProfile, author) => {
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

  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const candidate = useSelector((state) => state.candidate);
  const obj = isCandidate ? candidate : source;
  const spectra = useSelector((state) => state.spectra);
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const earthquake = useSelector((state) => state.earthquake);
  const userProfile = useSelector((state) => state.profile);
  const permissions = useSelector((state) => state.profile.permissions);
  const compactComments = useSelector(
    (state) => state.profile.preferences?.compactComments,
  );
  const { currentShift } = useSelector((state) => state.shift);

  const { showBotComments } = useSelector((state) => state.profile.preferences);

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

  if (!shiftID && currentShift) {
    shiftID = currentShift.id;
  }

  if (!earthquakeID && earthquake) {
    earthquakeID = earthquake.id;
  }

  const addComment = (formData) => {
    dispatch(
      sourceActions.addComment({
        obj_id: objID,
        spectrum_id: spectrumID,
        ...formData,
      }),
    );
  };

  const addGcnEventComment = (formData) => {
    dispatch(
      gcnEventActions.addCommentOnGcnEvent({
        gcnevent_id: gcnEventID,
        ...formData,
      }),
    );
  };

  const addEarthquakeComment = (formData) => {
    dispatch(
      earthquakeActions.addCommentOnEarthquake({
        earthquake_id: earthquakeID,
        ...formData,
      }),
    );
  };

  const addShiftComment = (formData) => {
    dispatch(
      shiftActions.addCommentOnShift({
        shiftID,
        ...formData,
      }),
    );
  };

  let comments = null;
  let specComments = null;

  if (associatedResourceType === "object") {
    comments = obj.comments;
    if (
      includeCommentsOnAllResourceTypes &&
      typeof spectra === "object" &&
      spectra !== null &&
      objID in spectra
    ) {
      specComments = spectra[objID]?.map((spec) => spec.comments)?.flat();
    }
    if (comments !== null && specComments !== null) {
      comments = specComments.concat(comments);
      comments.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
    }
  } else if (associatedResourceType === "spectra") {
    if (spectrumID === null) {
      throw new Error("Must specify a spectrumID for comments on spectra");
    }
    const spectrum = spectra[objID].find((spec) => spec.id === spectrumID);
    comments = spectrum?.comments;
  } else if (associatedResourceType === "gcn_event") {
    if (gcnEventID === null) {
      throw new Error("Must specify a gcnEventID for comments on gcnEvent");
    }
    comments = gcnEvent.comments;
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
    comments = earthquake.comments;
  } else {
    throw new Error(`Illegal input ${associatedResourceType} to CommentList. `);
  }

  comments = comments || [];

  if (!includeBots) {
    comments = comments?.filter((comment) => comment.bot === false);
  }

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme,
  );
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
          }) => (
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
              {compactComments ? (
                <CompactCommentList
                  associatedResourceType={resourceType}
                  styles={styles}
                  id={id}
                  objID={objID}
                  gcnEventID={gcnEventID}
                  earthquakeID={earthquakeID}
                  author={author}
                  created_at={created_at}
                  text={text}
                  spectrum_id={spectrum_id}
                  hoverID={hoverID}
                  shiftID={shiftID}
                />
              ) : (
                <RegularCommentList
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
              )}
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
              title="Include Bots?"
              type="checkbox"
              onChange={(event) => setIncludeBots(event.target.checked)}
              checked={includeBots || false}
            />
          }
        />
      </div>
      {permissions.indexOf("Comment") >= 0 &&
        objID &&
        (associatedResourceType === "object" ||
          associatedResourceType === "spectra") && (
          <CommentEntry addComment={addComment} />
        )}
      {permissions.indexOf("Comment") >= 0 &&
        gcnEventID &&
        associatedResourceType === "gcn_event" && (
          <CommentEntry addComment={addGcnEventComment} />
        )}
      {permissions.indexOf("Comment") >= 0 &&
        shiftID &&
        associatedResourceType === "shift" && (
          <CommentEntry addComment={addShiftComment} />
        )}
      {permissions.indexOf("Comment") >= 0 &&
        earthquakeID &&
        associatedResourceType === "earthquake" && (
          <CommentEntry addComment={addEarthquakeComment} />
        )}
    </div>
  );
};

CommentList.propTypes = {
  isCandidate: PropTypes.bool,
  objID: PropTypes.string,
  gcnEventID: PropTypes.number,
  earthquakeID: PropTypes.string,
  associatedResourceType: PropTypes.string,
  spectrumID: PropTypes.number,
  shiftID: PropTypes.number,
  includeCommentsOnAllResourceTypes: PropTypes.bool,
  maxHeightList: PropTypes.string,
};

CommentList.defaultProps = {
  isCandidate: false,
  objID: null,
  gcnEventID: null,
  earthquakeID: null,
  associatedResourceType: "object",
  spectrumID: null,
  shiftID: null,
  includeCommentsOnAllResourceTypes: true,
  maxHeightList: "350px",
};

export default CommentList;

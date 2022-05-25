import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSelector, useDispatch } from "react-redux";

import PropTypes from "prop-types";

import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";
import CloseIcon from "@material-ui/icons/Close";
import { makeStyles } from "@material-ui/core/styles";
import InfoOutlinedIcon from "@material-ui/icons/InfoOutlined";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import * as sourceActions from "../ducks/source";
import * as gcnEventActions from "../ducks/gcnEvent";
import * as shiftActions from "../ducks/shift";

import CommentEntry from "./CommentEntry";
import UserAvatar from "./UserAvatar";
import CommentAttachmentPreview from "./CommentAttachmentPreview";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  commentsContainer: {
    width: "100%",
  },
  commentsList: {
    marginTop: "1rem",
    overflowY: "scroll",
    maxHeight: "350px",
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
    maxWidth: "25em",
    "& > p": {
      margin: "0",
    },
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
  shiftID = null,
  includeCommentsOnAllResourceTypes = true,
}) => {
  const styles = useStyles();
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
  const userProfile = useSelector((state) => state.profile);
  const permissions = useSelector((state) => state.profile.permissions);
  const compactComments = useSelector(
    (state) => state.profile.preferences?.compactComments
  );
  const { currentShift } = useSelector((state) => state.shift);

  if (!objID && obj) {
    objID = obj.id;
  }

  if (!gcnEventID && gcnEvent) {
    gcnEventID = gcnEvent.id;
  }

  if (currentShift) {
    shiftID = currentShift.id;
  }

  const addComment = (formData) => {
    dispatch(
      sourceActions.addComment({
        obj_id: objID,
        spectrum_id: spectrumID,
        ...formData,
      })
    );
  };

  const addGcnEventComment = (formData) => {
    dispatch(
      gcnEventActions.addCommentOnGcnEvent({
        gcnevent_id: gcnEventID,
        ...formData,
      })
    );
  };

  const addShiftComment = (formData) => {
    dispatch(
      shiftActions.addCommentOnShift({
        shift_id: shiftID,
        ...formData,
      })
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
  } else {
    throw new Error(`Illegal input ${associatedResourceType} to CommentList. `);
  }

  comments = comments || [];

  const renderCommentText = (text, spectrum_id) => {
    if (
      spectrum_id &&
      objID in spectra &&
      associatedResourceType === "object"
    ) {
      const spectrum = spectra[objID].find((spec) => spec.id === spectrum_id);
      const dayFraction =
        (parseFloat(spectrum.observed_at.substring(11, 13)) / 24) * 10;
      return `**Spectrum ${spectrum.observed_at.substring(
        2,
        10
      )}.${dayFraction.toFixed(0)}** ${text}`;
    }

    return text;
  };

  const deleteComment = (sourceID, commentID) => {
    dispatch(sourceActions.deleteComment(sourceID, commentID));
  };

  const deleteCommentOnSpectrum = (commentSpectrumID, commentID) => {
    dispatch(
      sourceActions.deleteCommentOnSpectrum(commentSpectrumID, commentID)
    );
  };

  const deleteCommentOnGcnEvent = (gcnID, commentID) => {
    dispatch(gcnEventActions.deleteCommentOnGcnEvent(gcnID, commentID));
  };

  const deleteCommentOnShift = (commentID) => {
    dispatch(shiftActions.deleteCommentOnShift(commentID));
  };

  const emojiSupport = (text) =>
    text.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name
    );

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  return (
    <div className={styles.commentsContainer}>
      <div className={styles.commentsList}>
        {comments?.map(
          ({
            id,
            author,
            created_at,
            text,
            attachment_name,
            groups,
            spectrum_id,
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
                <div className={styles.compactContainer}>
                  <div className={styles.commentUserAvatar}>
                    <UserAvatar
                      size={24}
                      firstName={author.first_name}
                      lastName={author.last_name}
                      username={author.username}
                      gravatarUrl={author.gravatar_url}
                    />
                  </div>
                  <div
                    className={styles.compactWrap}
                    name={`commentDiv${
                      (spectrum_id ? "Spectrum" : "Source") + id
                    }`}
                  >
                    <ReactMarkdown
                      source={renderCommentText(
                        text,
                        spectrum_id,
                        associatedResourceType
                      )}
                      escapeHtml={false}
                      className={styles.commentMessage}
                      renderers={{ text: emojiSupport }}
                    />
                    <div className={styles.compactButtons}>
                      <Tooltip
                        title={dayjs().to(dayjs.utc(`${created_at}Z`))}
                        placement="left"
                      >
                        <InfoOutlinedIcon fontSize="small" />
                      </Tooltip>
                      <div className={styles.spacer}>
                        {associatedResourceType === "gcn_event" && (
                          <Button
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
                            color="primary"
                            type="button"
                            name={`deleteCommentButtonGcnEvent${id}`}
                            onClick={() =>
                              deleteCommentOnGcnEvent(gcnEventID, id)
                            }
                            className="commentDelete"
                          >
                            <CloseIcon fontSize="small" />
                          </Button>
                        )}
                        {associatedResourceType === "shift" && (
                          <Button
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
                            color="primary"
                            type="button"
                            name={`deleteCommentButtonShift${id}`}
                            onClick={() => deleteCommentOnShift(id)}
                            className="commentDelete"
                          >
                            <CloseIcon fontSize="small" />
                          </Button>
                        )}
                        {(associatedResourceType === "object" ||
                          associatedResourceType === "spectra") && (
                          <Button
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
                            color="primary"
                            name={`deleteCommentButton${
                              (spectrum_id ? "Spectrum" : "Source") + id
                            }`}
                            onClick={() =>
                              spectrum_id
                                ? deleteCommentOnSpectrum(spectrum_id, id)
                                : deleteComment(objID, id)
                            }
                            className="commentDelete"
                          >
                            <CloseIcon fontSize="small" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <div className={styles.commentUserAvatar}>
                    <UserAvatar
                      size={24}
                      firstName={author.first_name}
                      lastName={author.last_name}
                      username={author.username}
                      gravatarUrl={author.gravatar_url}
                    />
                  </div>
                  <div className={styles.commentContent}>
                    <div className={styles.commentHeader}>
                      <div className={styles.commentHeaderContent}>
                        <span className={styles.commentUser}>
                          <span className={styles.commentUserName}>
                            {author.username}
                          </span>
                        </span>
                        <span className={styles.commentTime}>
                          {dayjs().to(dayjs.utc(`${created_at}Z`))}
                        </span>
                        <span className={styles.commentUserGroup}>
                          <Tooltip
                            title={groups
                              ?.map((group) => group.name)
                              ?.join(", ")}
                          >
                            <GroupIcon fontSize="small" viewBox="0 -2 24 24" />
                          </Tooltip>
                        </span>
                      </div>
                      <div className={styles.defaultCommentDelete}>
                        {associatedResourceType === "gcn_event" && (
                          <Button
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
                            color="primary"
                            type="button"
                            name={`deleteCommentButtonGcnEvent${id}`}
                            onClick={() =>
                              deleteCommentOnGcnEvent(gcnEventID, id)
                            }
                            className="commentDelete"
                          >
                            <CloseIcon fontSize="small" />
                          </Button>
                        )}
                        {associatedResourceType === "shift" && (
                          <Button
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
                            color="primary"
                            type="button"
                            name={`deleteCommentButtonShift${id}`}
                            onClick={() => deleteCommentOnShift(id)}
                            className="commentDelete"
                          >
                            <CloseIcon fontSize="small" />
                          </Button>
                        )}
                        {(associatedResourceType === "object" ||
                          associatedResourceType === "spectra") && (
                          <Button
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
                            color="primary"
                            type="button"
                            name={`deleteCommentButton${
                              (spectrum_id ? "Spectrum" : "Source") + id
                            }`}
                            onClick={() =>
                              spectrum_id
                                ? deleteCommentOnSpectrum(spectrum_id, id)
                                : deleteComment(objID, id)
                            }
                            className="commentDelete"
                          >
                            <CloseIcon fontSize="small" />
                          </Button>
                        )}
                      </div>
                    </div>
                    <div
                      className={styles.wrap}
                      name={`commentDiv${
                        (spectrum_id ? "Spectrum" : "Source") + id
                      }`}
                    >
                      <ReactMarkdown
                        source={renderCommentText(
                          text,
                          spectrum_id,
                          associatedResourceType
                        )}
                        escapeHtml={false}
                        className={styles.commentMessage}
                        renderers={{ text: emojiSupport }}
                      />
                    </div>
                    <span>
                      {attachment_name &&
                        (associatedResourceType === "object" ||
                          associatedResourceType === "spectra") && (
                          <CommentAttachmentPreview
                            filename={attachment_name}
                            objectID={spectrum_id || objID}
                            commentId={id}
                            associatedResourceType={
                              spectrum_id ? "spectra" : "sources"
                            }
                          />
                        )}
                      {attachment_name &&
                        associatedResourceType === "gcn_event" && (
                          <CommentAttachmentPreview
                            filename={attachment_name}
                            gcnEventID={gcnEventID}
                            commentId={id}
                            associatedResourceType="gcn_event"
                          />
                        )}
                      {attachment_name &&
                        associatedResourceType === "shift" && (
                          <CommentAttachmentPreview
                            filename={attachment_name}
                            shiftID={shiftID}
                            commentId={id}
                            associatedResourceType="shift"
                          />
                        )}
                    </span>
                  </div>
                </>
              )}
            </span>
          )
        )}
      </div>
      <br />
      {permissions.indexOf("Comment") >= 0 && objID && (
        <CommentEntry addComment={addComment} />
      )}
      {permissions.indexOf("Comment") >= 0 && gcnEventID && (
        <CommentEntry addComment={addGcnEventComment} />
      )}
      {permissions.indexOf("Comment") >= 0 && shiftID && (
        <CommentEntry addComment={addShiftComment} />
      )}
    </div>
  );
};

CommentList.propTypes = {
  isCandidate: PropTypes.bool,
  objID: PropTypes.string,
  gcnEventID: PropTypes.number,
  shiftID: PropTypes.number,
  associatedResourceType: PropTypes.string,
  spectrumID: PropTypes.number,
  includeCommentsOnAllResourceTypes: PropTypes.bool,
};

CommentList.defaultProps = {
  isCandidate: false,
  objID: null,
  gcnEventID: null,
  shiftID: null,
  associatedResourceType: "object",
  spectrumID: null,
  includeCommentsOnAllResourceTypes: true,
};

export default CommentList;

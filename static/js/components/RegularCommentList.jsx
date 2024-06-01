import React from "react";
import ReactMarkdown from "react-markdown";
import { useSelector } from "react-redux";

import PropTypes from "prop-types";

import Tooltip from "@mui/material/Tooltip";
import GroupIcon from "@mui/icons-material/Group";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import UserAvatar from "./user/UserAvatar";

import CommentAttachmentPreview from "./comment/CommentAttachmentPreview";
import DeleteComment from "./DeleteComment";
import EditComment from "./EditComment";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const RegularCommentList = ({
  associatedResourceType = "object",
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
  hoverID = null,
  shiftID = null,
}) => {
  const spectra = useSelector((state) => state.spectra);

  const renderCommentText = () => {
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
        10,
      )}.${dayFraction.toFixed(0)}** ${text}`;
    }

    return text;
  };

  const emojiSupport = (textComment) =>
    textComment.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name,
    );

  const commentMessageStyle =
    associatedResourceType === "shift"
      ? styles.commentMessageShift
      : styles.commentMessage;

  return (
    <>
      <div className={styles.commentUserAvatar}>
        <UserAvatar
          size={24}
          firstName={author.first_name}
          lastName={author.last_name}
          username={author.username}
          gravatarUrl={author.gravatar_url}
          isBot={author?.is_bot || false}
        />
      </div>
      <div className={styles.commentContent}>
        <div className={styles.commentHeader}>
          <div className={styles.commentHeaderContent}>
            <span className={styles.commentUser}>
              <span className={styles.commentUserName}>{author.username}</span>
            </span>
            <span className={styles.commentTime}>
              {dayjs().to(dayjs.utc(`${created_at}Z`))}
            </span>
            <span className={styles.commentUserGroup}>
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
            }}
          >
            <EditComment
              associatedResourceType={associatedResourceType}
              objID={objID}
              gcnEventID={gcnEventID}
              earthquakeID={earthquakeID}
              spectrum_id={spectrum_id}
              shiftID={shiftID}
              hoverID={hoverID}
              id={id}
              commentText={text}
              attachmentName={attachment_name}
            />
            <DeleteComment
              associatedResourceType={associatedResourceType}
              objID={objID}
              gcnEventID={gcnEventID}
              earthquakeID={earthquakeID}
              spectrum_id={spectrum_id}
              shiftID={shiftID}
              hoverID={hoverID}
              id={id}
            />
          </div>
        </div>
        <div
          className={styles.wrap}
          name={`commentDiv${(spectrum_id ? "Spectrum" : "Source") + id}`}
        >
          <ReactMarkdown
            className={commentMessageStyle}
            components={{ text: emojiSupport }}
          >
            {renderCommentText()}
          </ReactMarkdown>
        </div>
        <span>
          {attachment_name &&
            (associatedResourceType === "object" ||
              associatedResourceType === "spectra") && (
              <CommentAttachmentPreview
                filename={attachment_name}
                objectID={spectrum_id || objID}
                commentId={id}
                associatedResourceType={spectrum_id ? "spectra" : "sources"}
              />
            )}
          {attachment_name && associatedResourceType === "gcn_event" && (
            <CommentAttachmentPreview
              filename={attachment_name}
              gcnEventID={gcnEventID}
              commentId={id}
              associatedResourceType="gcn_event"
            />
          )}
          {attachment_name && associatedResourceType === "shift" && (
            <CommentAttachmentPreview
              filename={attachment_name}
              shiftID={shiftID}
              commentId={id}
              associatedResourceType="shift"
            />
          )}
          {attachment_name && associatedResourceType === "earthquake" && (
            <CommentAttachmentPreview
              filename={attachment_name}
              earthquakeID={earthquakeID}
              commentId={id}
              associatedResourceType="earthquake"
            />
          )}
        </span>
      </div>
    </>
  );
};

RegularCommentList.propTypes = {
  objID: PropTypes.string,
  gcnEventID: PropTypes.number,
  earthquakeID: PropTypes.string,
  associatedResourceType: PropTypes.string,
  styles: PropTypes.shape({}),
  id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  author: PropTypes.shape({}),
  created_at: PropTypes.string,
  text: PropTypes.string,
  attachment_name: PropTypes.string,
  groups: PropTypes.arrayOf(PropTypes.shape({})),
  spectrum_id: PropTypes.string,
  hoverID: PropTypes.number,
  shiftID: PropTypes.number,
};

RegularCommentList.defaultProps = {
  objID: null,
  gcnEventID: null,
  earthquakeID: null,
  associatedResourceType: "object",
  styles: {},
  id: null,
  author: {},
  created_at: null,
  text: null,
  attachment_name: null,
  groups: [],
  spectrum_id: null,
  hoverID: null,
  shiftID: null,
};

export default RegularCommentList;

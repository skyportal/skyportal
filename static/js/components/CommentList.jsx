import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";
import CloseIcon from "@material-ui/icons/Close";
import InfoOutlinedIcon from "@material-ui/icons/InfoOutlined";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import * as sourceActions from "../ducks/source";
import styles from "./CommentList.css";
import CommentEntry from "./CommentEntry";
import UserAvatar from "./UserAvatar";
import CommentAttachmentPreview from "./CommentAttachmentPreview";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const CommentList = () => {
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
  const obj = useSelector((state) => state.source);
  const userProfile = useSelector((state) => state.profile);
  const permissions = useSelector((state) => state.profile.permissions);
  const compactComments = useSelector(
    (state) => state.profile.preferences.compactedComments
  );

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  let { comments } = obj;
  const addComment = (formData) => {
    dispatch(sourceActions.addComment({ obj_id: obj.id, ...formData }));
  };

  comments = comments || [];

  const emojiSupport = (text) =>
    text.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name
    );

  return (
    <div>
      <div className={styles.commentsList}>
        {comments.map(
          ({ id, author, created_at, text, attachment_name, groups }) => (
            <span
              key={id}
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
                  <div className={styles.compactWrap} name={`commentDiv${id}`}>
                    <ReactMarkdown
                      source={text}
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
                          name={`deleteCommentButton${id}`}
                          onClick={() => {
                            dispatch(sourceActions.deleteComment(id));
                          }}
                          className={styles.commentDelete}
                        >
                          <CloseIcon fontSize="small" />
                        </Button>
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
                        <div className={styles.commentUserGroup}>
                          <Tooltip
                            title={groups.map((group) => group.name).join(", ")}
                          >
                            <GroupIcon fontSize="small" viewBox="0 -2 24 24" />
                          </Tooltip>
                        </div>
                      </div>
                      <div className={styles.defaultCommentDelete}>
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
                          name={`deleteCommentButton${id}`}
                          onClick={() => {
                            dispatch(sourceActions.deleteComment(id));
                          }}
                          className={styles.commentDelete}
                        >
                          <CloseIcon fontSize="small" />
                        </Button>
                      </div>
                    </div>
                    <div className={styles.wrap} name={`commentDiv${id}`}>
                      <ReactMarkdown
                        source={text}
                        escapeHtml={false}
                        className={styles.commentMessage}
                        renderers={{ text: emojiSupport }}
                      />
                    </div>
                    <span>
                      {attachment_name && (
                        <CommentAttachmentPreview
                          filename={attachment_name}
                          commentId={id}
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
      {permissions.indexOf("Comment") >= 0 && (
        <CommentEntry addComment={addComment} />
      )}
    </div>
  );
};

export default CommentList;

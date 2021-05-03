import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";
import Checkbox from "@material-ui/core/Checkbox";

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
  const [compact, setCompact] = useState(false);

  const handleMouseHover = (id, userProfile, author) => {
    if (
      userProfile.roles.includes("Super admin") ||
      userProfile.username === author
    ) {
      setHoverID(id);
    }
  };

  const handleMouseLeave = () => {
    setHoverID(null);
  };

  const handleCompact = (event) => {
    setCompact(event.target.checked);
  };

  const dispatch = useDispatch();
  const obj = useSelector((state) => state.source);
  const userProfile = useSelector((state) => state.profile);
  const permissions = useSelector((state) => state.profile.permissions);

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
    <div className={styles.comments}>
      <div className={styles.commentsList}>
        <div>
          Compact
          <Checkbox
            checked={compact}
            onChange={handleCompact}
            inputProps={{ "aria-label": "primary checkbox" }}
          />
        </div>
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
              {compact ? (
                <div className={styles.compactContainer}>
                  <span className={styles.commentUserName}>
                    {author.username}
                  </span>
                  <div className={styles.compactWrap} name={`commentDiv${id}`}>
                    <ReactMarkdown
                      source={text}
                      escapeHtml={false}
                      className={styles.commentMessage}
                      renderers={{ text: emojiSupport }}
                    />
                    <Button
                      style={
                        hoverID === id
                          ? { display: "block" }
                          : { display: "block" }
                      }
                      size="small"
                      color="primary"
                      name={`deleteCommentButton${id}`}
                      onClick={() => {
                        dispatch(sourceActions.deleteComment(id));
                      }}
                      className={styles.commentDelete}
                    >
                      X
                    </Button>
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

                    <div className={styles.wrap} name={`commentDiv${id}`}>
                      <ReactMarkdown
                        source={text}
                        escapeHtml={false}
                        className={styles.commentMessage}
                        renderers={{ text: emojiSupport }}
                      />
                      <Button
                        style={
                          hoverID === id
                            ? { display: "block" }
                            : { display: "none" }
                        }
                        size="small"
                        variant="outlined"
                        color="primary"
                        type="button"
                        name={`deleteCommentButton${id}`}
                        onClick={() => {
                          dispatch(sourceActions.deleteComment(id));
                        }}
                        className={styles.commentDelete}
                      >
                        🗑
                      </Button>
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

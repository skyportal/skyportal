import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as sourceActions from "../ducks/source";
import styles from "./CommentList.css";
import CommentEntry from "./CommentEntry";
import UserAvatar from "./UserAvatar";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const CommentList = ({ isCandidate }) => {
  const [hoverID, setHoverID] = useState(null);

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

  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const candidate = useSelector((state) => state.candidate);
  const obj = isCandidate ? candidate : source;
  const userProfile = useSelector((state) => state.profile);
  const acls = useSelector((state) => state.profile.acls);

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

  const items = comments.map(
    ({
      id,
      author,
      author_info,
      created_at,
      text,
      attachment_name,
      groups,
    }) => {
      return (
        <span
          key={id}
          className={commentStyle}
          onMouseOver={() => handleMouseHover(id, userProfile, author.username)}
          onMouseOut={() => handleMouseLeave()}
          onFocus={() => handleMouseHover(id, userProfile, author.username)}
          onBlur={() => handleMouseLeave()}
        >
          <div className={styles.commentUserAvatar}>
            <UserAvatar
              size={24}
              firstName={author_info.first_name}
              lastName={author_info.last_name}
              username={author_info.username}
              gravatarUrl={author_info.gravatar_url}
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
                <Tooltip title={groups.map((group) => group.name).join(", ")}>
                  <GroupIcon fontSize="small" viewBox="0 -2 24 24" />
                </Tooltip>
              </div>
            </div>
            <div className={styles.wrap} name={`commentDiv${id}`}>
              <div className={styles.commentMessage}>{text}</div>
              <Button
                style={
                  hoverID === id ? { display: "block" } : { display: "none" }
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
                <div>
                  Attachment:&nbsp;
                  <a href={`/api/comment/${id}/attachment`}>
                    {attachment_name}
                  </a>
                </div>
              )}
            </span>
          </div>
        </span>
      );
    }
  );
  return (
    <div className={styles.comments}>
      <div className={styles.commentsList}>{items}</div>
      <br />
      {!isCandidate && acls.indexOf("Comment") >= 0 && (
        <CommentEntry addComment={addComment} />
      )}
    </div>
  );
};

CommentList.propTypes = {
  isCandidate: PropTypes.bool,
};

CommentList.defaultProps = {
  isCandidate: false,
};

export default CommentList;

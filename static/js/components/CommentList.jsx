import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

import * as sourceActions from "../ducks/source";
import styles from "./CommentList.css";
import CommentEntry from "./CommentEntry";

dayjs.extend(relativeTime);

const CommentList = () => {
  const [hoverID, setHoverID] = useState(null);

  const handleMouseHover = (id, userProfile, author) => {
    if (userProfile.roles.includes("Super admin") || userProfile.username === author) {
      setHoverID(id);
    }
  };

  const handleMouseLeave = () => {
    setHoverID(null);
  };

  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const userProfile = useSelector((state) => state.profile);
  const acls = useSelector((state) => state.profile.acls);
  let { comments } = source;
  const addComment = (formData) => {
    dispatch(sourceActions.addComment({ obj_id: source.id, ...formData }));
  };

  comments = comments || [];

  const items = comments.map(
    ({ id, author, created_at, text, attachment_name }) => (
      <span
        key={id}
        className={styles.comment}
        onMouseOver={() => handleMouseHover(id, userProfile, author)}
        onMouseOut={() => handleMouseLeave()}
        onFocus={() => handleMouseHover(id, userProfile, author)}
        onBlur={() => handleMouseLeave()}
      >
        <div className={styles.commentHeader}>
          <span className={styles.commentUser}>
            <span className={styles.commentUserName}>
              {author}
            </span>
          </span>
          &nbsp;
          <span className={styles.commentTime}>
            {dayjs().to(dayjs(created_at))}
          </span>
        </div>
        <div className={styles.wrap} name={`commentDiv${id}`}>
          <div className={styles.commentMessage}>
            {text}
          </div>
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
        {
          attachment_name && (
            <div>
              Attachment:&nbsp;
              <a href={`/api/comment/${id}/attachment`}>
                {attachment_name}
              </a>
            </div>
          )
        }
      </span>
    )
  );
  return (
    <div className={styles.comments}>
      {items}
      <br />
      {
        (acls.indexOf('Comment') >= 0) &&
        <CommentEntry addComment={addComment} />
      }
    </div>
  );
};

export default CommentList;

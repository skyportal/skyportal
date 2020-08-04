import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";

import dayjs from "dayjs";
import utc from 'dayjs/plugin/utc';
import relativeTime from "dayjs/plugin/relativeTime";

import * as sourceActions from "../ducks/source";
import styles from "./CommentList.css";
import CommentEntry from "./CommentEntry";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const CommentList = ({ isCandidate }) => {
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
  const candidate = useSelector((state) => state.candidate);
  const obj = isCandidate ? candidate : source;
  const userProfile = useSelector((state) => state.profile);
  const acls = useSelector((state) => state.profile.acls);
  let { comments } = obj;
  const addComment = (formData) => {
    dispatch(sourceActions.addComment({ obj_id: obj.id, ...formData }));
  };

  comments = comments || [];

  const items = comments.map(
    ({ id, author, created_at, text, attachment_name, groups }) => (
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
            {dayjs().to(dayjs.utc(`${created_at}Z`))}
          </span>
          &nbsp;
          <Tooltip title={groups.map((group) => group.name).join(", ")}>
            <GroupIcon fontSize="small" style={{ paddingTop: "6px", paddingBottom: "0px" }} />
          </Tooltip>
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
        (!isCandidate && (acls.indexOf('Comment') >= 0)) &&
        <CommentEntry addComment={addComment} />
      }
    </div>
  );
};

CommentList.propTypes = {
  isCandidate: PropTypes.bool
};

CommentList.defaultProps = {
  isCandidate: false
};

export default CommentList;

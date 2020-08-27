import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import styles from "./CommentList.css";
import UserAvatar from "./UserAvatar";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const CandidateCommentList = ({ comments }) => {
  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  const items = comments.map(
    ({ id, author, author_info, created_at, text, attachment_name }) => {
      return (
        <span key={id} className={commentStyle}>
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
                <span className={styles.commentUserName}>{author}</span>
              </span>
              <span className={styles.commentTime}>
                {dayjs().to(dayjs.utc(`${created_at}Z`))}
              </span>
            </div>
            <div className={styles.wrap} name={`commentDiv${id}`}>
              <div className={styles.commentMessage}>{text}</div>
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

  return <div>{items}</div>;
};

CandidateCommentList.propTypes = {
  comments: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default CandidateCommentList;

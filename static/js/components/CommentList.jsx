import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment-timezone';

import styles from './CommentList.css';
import CommentEntry from './CommentEntry';


const CommentList = ({ source_id, comments, addComment }) => {
  comments = comments || [];
  const items = comments.map(
    ({ id, author, created_at, text, attachment_name, attachment_bytes }) => (
      <span key={id} className={styles.comment}>
        <div className={styles.commentHeader}>
          <span className={styles.commentUser}>
            <span className={styles.commentUserName}>
              {author}
            </span>
          </span>
          &nbsp;
          <span className={styles.commentTime}>
            {moment(created_at).tz(Intl.DateTimeFormat().resolvedOptions().timeZone).calendar()}
          </span>
        </div>
        <div className={styles.commentMessage}>
          {text}
        </div>
        {attachment_name &&
        <div>
          Attachment:&nbsp;
          <a href={`/api/comment/${id}/download_attachment`}>
            {attachment_name}
          </a>
        </div>
        }
      </span>
    )
  );
  return (
    <div className={styles.comments}>
      {items}
      <br />
      <CommentEntry addComment={addComment} />
    </div>
  );
};

CommentList.propTypes = {
  source_id: PropTypes.string.isRequired,
  comments: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.String,
    user: PropTypes.shape({
      username: PropTypes.string.isRequired
    }),
    created_at: PropTypes.string.isRequired,
    text: PropTypes.string.isRequired
  })).isRequired,
  addComment: PropTypes.func.isRequired
};

export default CommentList;

import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';

import styles from './CommentList.css';
import CommentEntry from './CommentEntry';


const CommentList = ({ source_id, comments, addComment }) => {
  comments = comments || [];
  const items = comments.map(({ id, user, created_at, text }) => {
    const [username, domain] = user.username.split('@', 2);
    return (
      <span key={id} className={styles.comment}>
        <div className={styles.commentHeader}>
          <span className={styles.commentUser}>
            <span className={styles.commentUserName}>
              {username}
            </span>
            <span className={styles.commentUserDomain}>
@
              {domain}
            </span>
          </span>
          &nbsp;
          <span className={styles.commentTime}>
            {moment(created_at).calendar()}
          </span>
        </div>
        <div className={styles.commentMessage}>
          {text}
        </div>
      </span>
    );
  });
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

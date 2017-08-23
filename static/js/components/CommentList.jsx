import React from 'react';
import PropTypes from 'prop-types';

import styles from './CommentList.css';
import CommentEntry from './CommentEntry';


const CommentList = ({ source_id, comments, addComment }) => {
  comments = comments || [];
  const items = comments.map(({ id, user, created_at, text }) => (
    <span key={id}>
      <div className={styles.commentHeader}>
        On {created_at}, {user.username} wrote:
      </div>
      <div className={styles.commentMessage}>
        {text}
      </div>
    </span>
  ));
  return (
    <div className={styles.comments}>
      <b>Comments</b><br />
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
    username: PropTypes.String,
    created_at: PropTypes.String,
    text: PropTypes.string
  })).isRequired,
  addComment: PropTypes.func.isRequired
};

export default CommentList;

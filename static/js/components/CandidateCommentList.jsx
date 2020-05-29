import React from 'react';
import PropTypes from 'prop-types';

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

import styles from './CommentList.css';

dayjs.extend(relativeTime);


const CandidateCommentList = ({ comments }) => {
  const items = comments.map(({ id, author, created_at, text }) => (
    <span key={id} className={styles.comment}>
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
      <div className={styles.commentMessage}>
        {text}
      </div>
    </span>
  ));

  return (
    <div>
      {items}
    </div>
  );
};

CandidateCommentList.propTypes = {
  comments: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default CandidateCommentList;

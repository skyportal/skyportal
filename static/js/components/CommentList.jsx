import React from 'react';
import styles from './CommentList.css';
import CommentEntry from './CommentEntry';


const CommentList = ({source_id, comments, addComment}) => {
  comments = comments || [];
  const items = comments.map(({id, username, created_at, text}) => (
    <span key={id}>
      <div className={styles.commentHeader}>
        On {created_at}, {username} wrote:
      </div>
      <div className={styles.commentMessage}>
        {text}
      </div>
    </span>
  ));
  return (
    <div className={styles.comments}>
      <b>Comments</b><br/>
      {items}
      <br/>
      <CommentEntry source_id={source_id} addComment={addComment}/>
    </div>
  );
};

export default CommentList;

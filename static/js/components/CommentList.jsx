import React from 'react';
import styles from './CommentList.css';
import CommentEntry from './CommentEntry';


const CommentList = ({source, comments}) => {
  comments = comments || [];
  const items = comments.map(({id, user_id, created, text}) => (
    <span key={id}>
      <div className={styles.commentHeader}>
        On {created}, user {user_id} wrote:
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
      <CommentEntry source={source} handleSubmit={x => console.log(x)}/>
    </div>
  );
};

export default CommentList;

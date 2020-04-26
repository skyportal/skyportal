import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

import * as sourceActions from '../ducks/source';
import styles from './CommentList.css';
import CommentEntry from './CommentEntry';

dayjs.extend(relativeTime);


const CommentList = () => {

  const [isHover, setIsHover] = useState([]); 


  const handleMouseHover = (id, userProfile, author) => {  
    if (userProfile.roles.includes("Super admin") || userProfile.username === author) {
      let newState = [...isHover, id];
      setIsHover(newState);
      console.log(newState);
    }
    
  }

  const handleMouseLeave = (id) => {
    let newState = isHover.filter((cid) => cid !== id);
    setIsHover(newState);
    console.log(newState);
  }

  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const userProfile = useSelector((state) => state.profile);
  const acls = useSelector((state) => state.profile.acls);
  let { comments } = source;
  const addComment = (formData) => dispatch(
    sourceActions.addComment({ source_id: source.id, ...formData })
  );

  comments = comments || [];

  const items = comments.map(
    ({ id, author, created_at, text, attachment_name }) => (
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
        <div>
          <div onMouseOver={() => handleMouseHover(id, userProfile, author)} onMouseOut={() => handleMouseLeave(id)} className={styles.commentMessage}>
            {text}
          </div>
          {
            isHover.includes(id) && 
              <button
                type="button"
                onClick={() => dispatch(sourceActions.deleteComment(id))}
                className={styles.commentDelete}
              >
                🗑
              </button>
          }
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

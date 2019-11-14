import React from 'react';
import moment from 'moment-timezone';
import { useSelector, useDispatch } from 'react-redux';

import * as sourceActions from '../ducks/source';
import styles from './CommentList.css';
import CommentEntry from './CommentEntry';


const CommentList = () => {
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
        {
          userProfile.roles.includes("Super admin") || userProfile.username === author ? (
            <a href="#" onClick={() => dispatch(sourceActions.deleteComment(id))} className={styles.commentDelete}>
              Delete Comment
            </a>
          ) : null
        }
        {
          attachment_name && (
            <div>
              Attachment:&nbsp;
              <a href={`/api/comment/${id}/download_attachment`}>
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

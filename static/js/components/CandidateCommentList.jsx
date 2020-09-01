import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import Tooltip from "@material-ui/core/Tooltip";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import styles from "./CommentList.css";
import UserAvatar from "./UserAvatar";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  commentListContainer: {
    height: "100%",
    overflowY: "scroll",
    padding: "0.5rem 0",
  },
}));

const CandidateCommentList = ({ comments }) => {
  const classes = useStyles();

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  const items = comments.map(
    ({ id, author, author_info, created_at, text }) => {
      return (
        <span key={id} className={commentStyle}>
          <Tooltip title={author} arrow placement="top-start">
            <div className={styles.commentUserAvatar}>
              <UserAvatar
                size={24}
                firstName={author_info.first_name}
                lastName={author_info.last_name}
                username={author_info.username}
                gravatarUrl={author_info.gravatar_url}
              />
            </div>
          </Tooltip>
          <div className={styles.commentContent}>
            <span className={styles.commentMessage}>{text}</span>
            <span className={styles.commentTime}>
              {dayjs().to(dayjs.utc(`${created_at}Z`))}
            </span>
          </div>
        </span>
      );
    }
  );

  return <div className={classes.commentListContainer}>{items}</div>;
};

CandidateCommentList.propTypes = {
  comments: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default CandidateCommentList;

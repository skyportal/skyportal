import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import { Button } from "@material-ui/core";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";
import { makeStyles, withStyles } from "@material-ui/core/styles";
import ChatBubbleOutlineIcon from "@material-ui/icons/ChatBubbleOutline";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import MuiDialogTitle from "@material-ui/core/DialogTitle";
import IconButton from "@material-ui/core/IconButton";
import CloseIcon from "@material-ui/icons/Close";
import Typography from "@material-ui/core/Typography";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import * as sourceActions from "../ducks/source";
import CommentList, { shortenFilename } from "./CommentList";
import styles from "./CommentList.css";
import UserAvatar from "./UserAvatar";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  container: {
    height: "90%",
  },
  commentsList: {
    marginTop: "1rem",
    padding: "0.25rem",
  },
  dialogButton: {
    textAlign: "center",
    margin: "1.5rem",
  },
}));

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: theme.palette.grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle disableTypography className={classes.root}>
      <Typography variant="h4">{children}</Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <CloseIcon />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
);

const CommentListMobile = ({ isCandidate }) => {
  const classes = useStyles();

  const [hoverID, setHoverID] = useState(null);

  const [open, setOpen] = useState(false);
  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleMouseHover = (id, userProfile, author) => {
    if (
      userProfile.roles.includes("Super admin") ||
      userProfile.username === author
    ) {
      setHoverID(id);
    }
  };

  const handleMouseLeave = () => {
    setHoverID(null);
  };

  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const candidate = useSelector((state) => state.candidate);
  const obj = isCandidate ? candidate : source;
  const userProfile = useSelector((state) => state.profile);

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  let { comments } = obj;

  comments = comments || [];

  const emojiSupport = (text) =>
    text.value.replace(/:\w+:/gi, (name) => emoji.getUnicode(name));

  return (
    <div className={classes.container}>
      <div className={classes.commentsList}>
        {comments
          .slice(0, 3)
          .map(
            ({
              id,
              author,
              author_info,
              created_at,
              text,
              attachment_name,
              groups,
            }) => (
              <span
                key={id}
                className={commentStyle}
                onMouseOver={() =>
                  handleMouseHover(id, userProfile, author.username)
                }
                onMouseOut={() => handleMouseLeave()}
                onFocus={() =>
                  handleMouseHover(id, userProfile, author.username)
                }
                onBlur={() => handleMouseLeave()}
              >
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
                      <span className={styles.commentUserName}>
                        {author.username}
                      </span>
                    </span>
                    <span className={styles.commentTime}>
                      {dayjs().to(dayjs.utc(`${created_at}Z`))}
                    </span>
                    <div className={styles.commentUserGroup}>
                      <Tooltip
                        title={groups.map((group) => group.name).join(", ")}
                      >
                        <GroupIcon fontSize="small" viewBox="0 -2 24 24" />
                      </Tooltip>
                    </div>
                  </div>
                  <div className={styles.wrap} name={`commentDiv${id}`}>
                    <ReactMarkdown
                      source={text}
                      escapeHtml={false}
                      className={styles.commentMessage}
                      renderers={{ text: emojiSupport }}
                    />
                    <Button
                      style={
                        hoverID === id
                          ? { display: "block" }
                          : { display: "none" }
                      }
                      size="small"
                      variant="outlined"
                      color="primary"
                      type="button"
                      name={`deleteCommentButton${id}`}
                      onClick={() => {
                        dispatch(sourceActions.deleteComment(id));
                      }}
                      className={styles.commentDelete}
                    >
                      🗑
                    </Button>
                  </div>
                  <span>
                    {attachment_name && (
                      <Tooltip title={attachment_name}>
                        <div>
                          Attachment:&nbsp;
                          <a href={`/api/comment/${id}/attachment`}>
                            {shortenFilename(attachment_name)}
                          </a>
                        </div>
                      </Tooltip>
                    )}
                  </span>
                </div>
              </span>
            )
          )}
      </div>
      <div className={classes.dialogButton}>
        <Button
          color="primary"
          variant="outlined"
          onClick={handleClickOpen}
          startIcon={<ChatBubbleOutlineIcon />}
        >
          Add & see more comments
        </Button>
      </div>
      <Dialog
        open={open}
        onClose={handleClose}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
        <DialogTitle onClose={handleClose}>Comments</DialogTitle>
        <DialogContent dividers>
          <CommentList isCandidate={isCandidate} />
        </DialogContent>
      </Dialog>
    </div>
  );
};

CommentListMobile.propTypes = {
  isCandidate: PropTypes.bool,
};

CommentListMobile.defaultProps = {
  isCandidate: false,
};

export default CommentListMobile;

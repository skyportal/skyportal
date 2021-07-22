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
import InfoOutlinedIcon from "@material-ui/icons/InfoOutlined";
import Typography from "@material-ui/core/Typography";
import grey from "@material-ui/core/colors/grey";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import * as sourceActions from "../ducks/source";
import CommentList from "./CommentList";
import CommmentAttachmentPreview from "./CommentAttachmentPreview";
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
  comment: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: "#e0e0e0",
    },
    "& .commentDelete": {
      "&:hover": {
        color: "#e63946",
      },
    },
  },
  commentDark: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: "#3a3a3a",
    },
    "& .commentDelete": {
      color: "#b1dae9",
      "&:hover": {
        color: "#e63946",
      },
    },
  },
  commentContent: {
    display: "flex",
    flexFlow: "column nowrap",
    padding: "0.3125rem 0.625rem 0.3125rem 0.875rem",
    borderRadius: "15px",
    width: "100%",
  },
  spacer: {
    width: "20px",
    padding: "0 10px",
  },
  commentHeader: {
    display: "flex",
    alignItems: "center",
  },
  commentHeaderContent: {
    width: "70%",
  },
  commentTime: {
    color: "gray",
    fontSize: "80%",
    marginRight: "1em",
  },
  commentMessage: {
    maxWidth: "25em",
    "& > p": {
      margin: "0",
    },
  },
  commentUserName: {
    fontWeight: "bold",
    marginRight: "0.5em",
    whiteSpace: "nowrap",
    color: "#76aace",
  },
  commentUserDomain: {
    color: "lightgray",
    fontSize: "80%",
    paddingRight: "0.5em",
  },
  commentUserAvatar: {
    display: "block",
    margin: "0.5em",
  },
  commentUserGroup: {
    display: "inline-block",
    "& > svg": {
      fontSize: "1rem",
    },
  },
  wrap: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: "27px",
    maxWidth: "25em",
  },
  compactContainer: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: "25px",
    margin: "0 15px",
    width: "100%",
  },
  compactWrap: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    padding: "0 5px",
  },
  compactButtons: {
    display: "flex",
    alignItems: "center",
  },
  defaultCommentDelete: {
    display: "flex",
    justifyContent: "end",
    width: "30%",
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
    color: grey[500],
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
  const styles = useStyles();

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
      userProfile.permissions.includes("System admin") ||
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
  const compactComments = useSelector(
    (state) => state.profile.preferences.compactComments
  );

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
    <div className={styles.container}>
      <div className={styles.commentsList}>
        {comments
          .slice(0, 3)
          .map(({ id, author, created_at, text, attachment_name, groups }) => (
            <span
              key={id}
              className={commentStyle}
              onMouseOver={() =>
                handleMouseHover(id, userProfile, author.username)
              }
              onMouseOut={() => handleMouseLeave()}
              onFocus={() => handleMouseHover(id, userProfile, author.username)}
              onBlur={() => handleMouseLeave()}
            >
              {compactComments ? (
                <div className={styles.compactContainer}>
                  <div className={styles.commentUserAvatar}>
                    <UserAvatar
                      size={24}
                      firstName={author.first_name}
                      lastName={author.last_name}
                      username={author.username}
                      gravatarUrl={author.gravatar_url}
                    />
                  </div>
                  <div className={styles.compactWrap} name={`commentDiv${id}`}>
                    <ReactMarkdown
                      source={text}
                      escapeHtml={false}
                      className={styles.commentMessage}
                      renderers={{ text: emojiSupport }}
                    />
                    <div className={styles.compactButtons}>
                      <Tooltip
                        title={dayjs().to(dayjs.utc(`${created_at}Z`))}
                        placement="left"
                      >
                        <InfoOutlinedIcon fontSize="small" />
                      </Tooltip>
                      <div className={styles.spacer}>
                        <Button
                          style={
                            hoverID === id
                              ? {
                                  display: "block",
                                  minWidth: "0",
                                  lineHeight: "0",
                                  padding: "0",
                                }
                              : { display: "none" }
                          }
                          size="small"
                          color="primary"
                          name={`deleteCommentButton${id}`}
                          onClick={() => {
                            dispatch(sourceActions.deleteComment(id));
                          }}
                          className="commentDelete"
                        >
                          <CloseIcon fontSize="small" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <div className={styles.commentUserAvatar}>
                    <UserAvatar
                      size={24}
                      firstName={author.first_name}
                      lastName={author.last_name}
                      username={author.username}
                      gravatarUrl={author.gravatar_url}
                    />
                  </div>
                  <div className={styles.commentContent}>
                    <div className={styles.commentHeader}>
                      <div className={styles.commentHeaderContent}>
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
                      <div className={styles.defaultCommentDelete}>
                        <Button
                          style={
                            hoverID === id
                              ? {
                                  display: "block",
                                  minWidth: "0",
                                  lineHeight: "0",
                                  padding: "0",
                                }
                              : { display: "none" }
                          }
                          size="small"
                          color="primary"
                          type="button"
                          name={`deleteCommentButton${id}`}
                          onClick={() => {
                            dispatch(sourceActions.deleteComment(id));
                          }}
                          className="commentDelete"
                        >
                          <CloseIcon fontSize="small" />
                        </Button>
                      </div>
                    </div>
                    <div className={styles.wrap} name={`commentDiv${id}`}>
                      <ReactMarkdown
                        source={text}
                        escapeHtml={false}
                        className={styles.commentMessage}
                        renderers={{ text: emojiSupport }}
                      />
                    </div>
                    <span>
                      {attachment_name && (
                        <CommmentAttachmentPreview
                          filename={attachment_name}
                          commentId={id}
                        />
                      )}
                    </span>
                  </div>
                </>
              )}
            </span>
          ))}
      </div>
      <div className={styles.dialogButton}>
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

import React from "react";
import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";

import { Paper, Avatar, Tooltip } from "@material-ui/core";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import UserAvatar from "./UserAvatar";
import * as profileActions from "../ducks/profile";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  numItems: "10",
  categories: {
    classifications: true,
    comments: true,
    photometry: true,
    sources: true,
    spectra: true,
    includeCommentsFromBots: false,
  },
};

const useStyles = makeStyles((theme) => ({
  newsFeed: {
    display: "flex",
    flexDirection: "column",
    overflowY: "scroll",
    paddingTop: "0.3125rem",
    paddingLeft: "0.3125rem",
    marginTop: "0.625rem",
    backgroundColor: theme.palette.background.default,
  },
  entry: {
    display: "flex",
    flexDirection: "row",
    padding: "0.3125rem 0.625rem 0.625rem 0.3125rem",
    marginBottom: "0.625rem",
    marginRight: "0.3125rem",
    alignItems: "center",
  },
  entryMessage: {
    maxWidth: "350px",
    marginBottom: "0.2em",
    "& > p": {
      margin: 0,
    },
  },
  entryContent: {
    paddingTop: "0.3em",
    paddingBottom: "0.1em",
    display: "flex",
    flexDirection: "column",
  },
  entryAvatar: {
    marginRight: "0.6em",
  },
  entryIdent: {
    display: "flex",
    flexDirection: "row",
    alignItems: "baseline",
    color: "#aaa",
    fontSize: "80%",
  },
  entryTime: {
    marginLeft: "0.5em",
  },
  entrySourceId: {
    marginRight: "0.5em",
    fontSize: "105%",
    "& > a": {
      color: "#9b9a9a !important",
    },
  },
  entryTitle: {
    fontSize: "0.875em !important",
    padding: "0.3125rem 0.625rem !important",
  },
}));

const NewsFeedItem = ({ item }) => {
  const styles = useStyles();
  const emojiSupport = (text) =>
    text.value.replace(/:\w+:/gi, (name) => emoji.getUnicode(name));

  let EntryAvatar;
  let entryTitle;
  // Use switch-case to make it easy to add future newsfeed types
  switch (item.type) {
    case "comment":
    case "photometry":
    case "spectrum":
    case "classification":
      /* eslint-disable react/display-name */
      EntryAvatar = () => (
        <UserAvatar
          size={32}
          firstName={item.author_info.first_name}
          lastName={item.author_info.last_name}
          username={item.author_info.username}
          gravatarUrl={item.author_info.gravatar_url}
        />
      );
      entryTitle = null;
      break;
    case "source":
      /* eslint-disable react/display-name */
      EntryAvatar = () => (
        <Avatar
          alt="S"
          size={32}
          style={{
            width: 32,
            height: 32,
            backgroundColor: "#141b44",
            color: "white",
            fontSize: "10px",
          }}
        >
          S
        </Avatar>
      );
      /* eslint-disable react/display-name */
      entryTitle = "New source";
      break;
    default:
      break;
  }

  return (
    <Paper
      key={`newsFeedItem_${item.time}`}
      className={styles.entry}
      elevation={1}
    >
      {entryTitle !== null ? (
        <Tooltip
          title={entryTitle}
          arrow
          placement="top-start"
          classes={{ tooltip: styles.entryTitle }}
        >
          <div className={styles.entryAvatar}>
            <EntryAvatar />
          </div>
        </Tooltip>
      ) : (
        <div className={styles.entryAvatar}>
          <EntryAvatar />
        </div>
      )}
      <div className={styles.entryContent}>
        <ReactMarkdown
          source={item.message}
          className={styles.entryMessage}
          escapeHtml={false}
          renderers={{ text: emojiSupport }}
        />
        <div className={styles.entryIdent}>
          <span className={styles.entrySourceId}>
            <Link to={`/source/${item.source_id}`}>
              Source: {item.source_id}
            </Link>
          </span>
          <span> &#124; </span>
          <span className={styles.entryTime}>
            {dayjs().to(dayjs.utc(`${item.time}Z`))}
          </span>
        </div>
      </div>
    </Paper>
  );
};

const NewsFeed = ({ classes }) => {
  const styles = useStyles();
  const { items } = useSelector((state) => state.newsFeed);
  const newsFeedPrefs =
    useSelector((state) => state.profile.preferences.newsFeed) || defaultPrefs;
  if (!Object.keys(newsFeedPrefs).includes("categories")) {
    newsFeedPrefs.categories = defaultPrefs.categories;
  }

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography variant="h6" display="inline">
            News Feed
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              initialValues={newsFeedPrefs}
              stateBranchName="newsFeed"
              title="News Feed Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.newsFeed} style={{ height: "85%" }}>
          {items.map((item) => (
            <NewsFeedItem
              key={`${item.author}-${item.source_id}-${item.time}`}
              item={item}
            />
          ))}
        </div>
      </div>
    </Paper>
  );
};

NewsFeedItem.propTypes = {
  item: PropTypes.shape({
    type: PropTypes.string.isRequired,
    time: PropTypes.string.isRequired,
    message: PropTypes.string.isRequired,
    source_id: PropTypes.string.isRequired,
    author: PropTypes.string,
    author_info: PropTypes.shape({
      username: PropTypes.string.isRequired,
      first_name: PropTypes.string,
      last_name: PropTypes.string,
      gravatar_url: PropTypes.string.isRequired,
    }),
  }).isRequired,
};

NewsFeed.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default NewsFeed;

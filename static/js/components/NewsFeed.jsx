import React from "react";
import { useSelector } from "react-redux";
import { Paper, Avatar } from "@material-ui/core";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import UserAvatar from "./UserAvatar";
import * as profileActions from "../ducks/profile";
import styles from "./NewsFeed.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  numItems: "",
};

const newsFeedItem = (item) => {
  let EntryAvatar;
  let entryUserName;
  // Use switch-case to make it easy to add future newsfeed types
  switch (item.type) {
    case "comment":
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
      /* eslint-disable react/display-name */
      entryUserName = item.author;
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
            backgroundColor: "#38B0DE",
            color: "white",
            fontSize: "10px",
          }}
        >
          S
        </Avatar>
      );
      /* eslint-disable react/display-name */
      entryUserName = "New source";
      break;
    default:
      break;
  }

  return (
    <Paper
      key={`newsFeedItem_${item.time}`}
      className={styles.entry}
      elevation={2}
    >
      <div className={styles.entryHeader}>
        <div className={styles.entryAvatar}>
          <EntryAvatar />
        </div>
        <div className={styles.entryIdent}>
          <span className={styles.entryUser}>
            <span>{entryUserName}</span>
          </span>
          <span className={styles.entryTime}>
            {dayjs().to(dayjs.utc(`${item.time}Z`))}
          </span>
        </div>
      </div>
      <span className={styles.entryMessage}>{item.message}</span>
    </Paper>
  );
};

const NewsFeed = () => {
  const { items } = useSelector((state) => state.newsFeed);
  const newsFeedPrefs =
    useSelector((state) => state.profile.preferences.newsFeed) || defaultPrefs;

  return (
    <div style={{ border: "1px solid #DDD", padding: "10px" }}>
      <h2 style={{ display: "inline-block" }}>News Feed</h2>
      <div style={{ display: "inline-block", float: "right" }}>
        <WidgetPrefsDialog
          formValues={newsFeedPrefs}
          stateBranchName="newsFeed"
          title="News Feed Preferences"
          onSubmit={profileActions.updateUserPreferences}
        />
      </div>
      <div>
        <h4 className={styles.newsFeedSubtitle}>Most recent activity:</h4>
        <div className={styles.newsFeed}>
          {items.map((item) => newsFeedItem(item))}
        </div>
      </div>
    </div>
  );
};

export default NewsFeed;

import React from 'react';
import { useSelector } from 'react-redux';

import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

import WidgetPrefsDialog from './WidgetPrefsDialog';
import * as ProfileActions from '../ducks/profile';
import styles from './NewsFeed.css';

dayjs.extend(relativeTime);


const NewsFeed = () => {
  const { newsFeedItems } = useSelector((state) => state.newsFeed);
  const profile = useSelector((state) => state.profile);

  const newsFeedPrefs = (
    profile != null &&
    Object.prototype.hasOwnProperty.call(profile, "preferences") &&
    profile.preferences != null &&
    Object.prototype.hasOwnProperty.call(profile.preferences, "newsFeed")
  ) ?
    profile.preferences.newsFeed : { numItems: "" };
  if (newsFeedItems === undefined) {
    return (
      <div>
        No new items to display...
      </div>
    );
  }
  return (
    <div style={{ border: "1px solid #DDD", padding: "10px" }}>
      <h2 style={{ display: "inline-block" }}>
        News Feed
      </h2>
      <div style={{ display: "inline-block", float: "right" }}>
        <WidgetPrefsDialog
          formValues={newsFeedPrefs}
          stateBranchName="newsFeed"
          title="News Feed Preferences"
          onSubmit={ProfileActions.updateUserPreferences}
        />
      </div>
      <div>
        <h4>
          Newest Activity:
        </h4>
        <ul>
          {
            newsFeedItems.map((item) => (
              <li key={`newsFeedItem_${item.time}`}>
                <span className={styles.entryTime}>
                  {dayjs().to(dayjs(item.time))}
                </span>
                &nbsp;
                {item.type}
                :&nbsp;
                <span className={styles.entry}>
                  {item.message}
                </span>
              </li>
            ))
          }
        </ul>
      </div>
    </div>
  );
};

export default NewsFeed;

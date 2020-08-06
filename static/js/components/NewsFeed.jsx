import React from 'react';
import { useSelector } from 'react-redux';

import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import relativeTime from 'dayjs/plugin/relativeTime';

import WidgetPrefsDialog from './WidgetPrefsDialog';
import * as profileActions from '../ducks/profile';
import styles from './NewsFeed.css';

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  numItems: ""
};

const NewsFeed = () => {
  const { items } = useSelector((state) => state.newsFeed);
  const newsFeedPrefs = useSelector(
    (state) => state.profile.preferences.newsFeed
  ) || defaultPrefs;

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
          onSubmit={profileActions.updateUserPreferences}
        />
      </div>
      <div>
        <h4>
          Newest Activity:
        </h4>
        <ul>
          {
            items.map((item) => (
              <li key={`newsFeedItem_${item.time}`}>
                <span className={styles.entryTime}>
                  {dayjs().to(dayjs.utc(`${item.time}Z`))}
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

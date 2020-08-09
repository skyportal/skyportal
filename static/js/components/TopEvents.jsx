import React from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';

import * as profileActions from '../ducks/profile';
import WidgetPrefsDialog from './WidgetPrefsDialog';

import styles from "./TopEvents.css";

const defaultPrefs = {
  maxNumEvents: "",
  sinceDaysAgo: ""
};

const TopEvents = () => {
  const { eventViews } = useSelector((state) => state.topEvents);
  const topEventsPrefs = useSelector(
    (state) => state.profile.preferences.topEvents
  ) || defaultPrefs;

  return (
    <div className={styles.topEventsContainer}>
      <h2 style={{ display: "inline-block" }}>
        Top Events
      </h2>
      <div style={{ display: "inline-block", float: "right" }}>
        <WidgetPrefsDialog
          formValues={topEventsPrefs}
          stateBranchName="topEvents"
          title="Top Events Preferences"
          onSubmit={profileActions.updateUserPreferences}
        />
      </div>
      <p>
        Displaying most-viewed events
      </p>
      <ul className={styles.topSourceList}>
        {
          eventViews.map(({ dateobs, localizations, tags }) => (
            <li>
              <div>
                &nbsp;
                -&nbsp;
                <Link to={`/event/${dateobs}`}>
                  {dateobs}
                </Link>
              </div>
              <div>
                <em>
                  &nbsp;
                  -&nbsp;
                  {tags.map(function(tag, i){
                      return <span className={styles.tag} key={i}>{tag}</span>
                  })}
                </em>
              </div>
              <div>
                <em>
                  &nbsp;
                  -&nbsp;
                  {localizations.map(function(localization, i){
                      return <span className={styles.localization} key={i}>{localization}</span>
                  })}
                </em>
              </div>
            </li>
          ))
        }
      </ul>
    </div>
  );
};

export default TopEvents;

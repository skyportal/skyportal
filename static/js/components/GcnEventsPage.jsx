import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import styles from "./GcnEventsPage.css";

import * as gcnEventsActions from "../ducks/gcnEvents";

const GcnEventsPage = () => {
  const { gcnEvents } = useSelector((state) => state.gcnEvents);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(gcnEventsActions.fetchTopGcnEvents());
  }, [dispatch]);

  return (
    <div className={styles.topGcnEventsContainer}>
      <h2 style={{ display: "inline-block" }}>Top Events</h2>
      <p>Displaying most-viewed events</p>
      <ul className={styles.topGcnEventList}>
        {gcnEvents.map(({ dateobs, localizations, tags }) => (
          <li key={dateobs}>
            <div>
              &nbsp; -&nbsp;
              <Link to={`/gcnevents/${dateobs}`}>{dateobs}</Link>
            </div>
            <div>
              <em>
                &nbsp; -&nbsp;
                {tags.map((tag) => (
                  <span className={styles.tag} key={tag}>
                    {tag}
                  </span>
                ))}
              </em>
            </div>
            <div>
              <em>
                &nbsp; -&nbsp;
                {localizations.map((localization) => (
                  <span className={styles.localization} key={localization}>
                    <Link to={`/gcnevents/${dateobs}/${localization}`}>
                      {localization}
                    </Link>
                  </span>
                ))}
              </em>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default GcnEventsPage;

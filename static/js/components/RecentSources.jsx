import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { ra_to_hours, dec_to_hours } from "../units";

import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

import styles from "./RecentSources.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  maxNumSources: "5",
};

const RecentSources = () => {
  const { recentSources } = useSelector((state) => state.recentSources);
  const recentSourcesPrefs =
    useSelector((state) => state.profile.preferences.recentSources) ||
    defaultPrefs;

  const SourcesList = ({ sources }) => {
    return sources.length === 0 ? (
      <div>Loading recent sources...</div>
    ) : (
      <div>
        <ul className={styles.recentSourceList}>
          {sources.map(
            ({ obj_id, ra, dec, created_at, public_url, classifications }) => {
              // Add highest probability classification to the name
              let recentSourceName = `${obj_id}`;
              if (classifications.length > 0) {
                const highestProbClassification = classifications.sort(
                  (a, b) => b.probability - a.probability
                )[0].classification;

                recentSourceName += ` (${highestProbClassification})`;
              }

              return (
                <li key={`recentSources_${obj_id}`}>
                  <div className={styles.recentSourceItem}>
                    <Link
                      to={`/source/${obj_id}`}
                      className={styles.stampContainer}
                    >
                      <img
                        className={styles.stamp}
                        src={public_url}
                        alt={obj_id}
                      />
                    </Link>
                    <div className={styles.recentSourceInfo}>
                      <span className={styles.recentSourceName}>
                        <Link to={`/source/${obj_id}`}>{recentSourceName}</Link>
                      </span>
                      <span>
                        {`\u03B1, \u03B4: ${ra_to_hours(ra)} ${dec_to_hours(
                          dec
                        )}`}
                      </span>
                    </div>
                    <div className={styles.recentSourceTime}>
                      <span>{dayjs().to(dayjs.utc(`${created_at}Z`))}</span>
                    </div>
                  </div>
                </li>
              );
            }
          )}
        </ul>
      </div>
    );
  };

  SourcesList.propTypes = {
    sources: PropTypes.arrayOf(
      PropTypes.shape({
        obj_id: PropTypes.string.isRequired,
        ra: PropTypes.number,
        dec: PropTypes.number,
        created_at: PropTypes.string.isRequired,
        public_url: PropTypes.string.isRequired,
        classifications: PropTypes.arrayOf(
          PropTypes.shape({
            author_name: PropTypes.string,
            probability: PropTypes.number,
            modified: PropTypes.string,
            classification: PropTypes.string,
            id: PropTypes.number,
            obj_id: PropTypes.string,
            author_id: PropTypes.number,
            taxonomy_id: PropTypes.number,
            created_at: PropTypes.string,
          })
        ),
      })
    ).isRequired,
  };

  return (
    <div className={styles.recentSourcesContainer}>
      <h2 style={{ display: "inline-block" }}>Recently Added Sources</h2>
      <div style={{ display: "inline-block", float: "right" }}>
        <WidgetPrefsDialog
          formValues={recentSourcesPrefs}
          stateBranchName="recentSources"
          title="Recent Sources Preferences"
          onSubmit={profileActions.updateUserPreferences}
        />
      </div>
      <SourcesList sources={recentSources} />
    </div>
  );
};

export default RecentSources;

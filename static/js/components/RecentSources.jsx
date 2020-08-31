import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";

import { ra_to_hours, dec_to_hours } from "../units";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import SourceQuickView from "./SourceQuickView";

import styles from "./RecentSources.css";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  maxNumSources: "5",
};

const RecentSourcesList = ({ sources }) => {
  return sources.length === 0 ? (
    <div>Loading recent sources...</div>
  ) : (
    <div className={styles.recentSourceListContainer}>
      <ul className={styles.recentSourceList}>
        {sources.map((source) => {
          let recentSourceName = `${source.obj_id}`;
          if (source.classifications.length > 0) {
            // Display the most recent non-zero probability class
            const filteredClasses = source.classifications.filter(
              (i) => i.probability > 0
            );
            const sortedClasses = filteredClasses.sort((a, b) =>
              a.modified < b.modified ? 1 : -1
            );

            recentSourceName += ` (${sortedClasses[0].classification})`;
          }

          return (
            <li key={`recentSources_${source.obj_id}`}>
              <div className={styles.recentSourceItemWithButton}>
                <div className={styles.recentSourceItem}>
                  <Link
                    to={`/source/${source.obj_id}`}
                    className={styles.stampContainer}
                  >
                    <img
                      className={styles.stamp}
                      src={source.public_url}
                      alt={source.obj_id}
                    />
                  </Link>
                  <div className={styles.recentSourceInfo}>
                    <span className={styles.recentSourceName}>
                      <Link to={`/source/${source.obj_id}`}>
                        {`${recentSourceName}`}
                      </Link>
                    </span>
                    <span>
                      {`\u03B1, \u03B4: ${ra_to_hours(
                        source.ra
                      )} ${dec_to_hours(source.dec)}`}
                    </span>
                  </div>
                  <div className={styles.recentSourceTime}>
                    <span>
                      {dayjs().to(dayjs.utc(`${source.created_at}Z`))}
                    </span>
                  </div>
                </div>
                <SourceQuickView
                  sourceId={source.obj_id}
                  className={styles.quickViewButton}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

RecentSourcesList.propTypes = {
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      obj_id: PropTypes.string.isRequired,
      ra: PropTypes.number,
      dec: PropTypes.number,
      created_at: PropTypes.string.isRequired,
      public_url: PropTypes.string,
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

const RecentSources = () => {
  const { recentSources } = useSelector((state) => state.recentSources);
  const recentSourcesPrefs =
    useSelector((state) => state.profile.preferences.recentSources) ||
    defaultPrefs;

  return (
    <Paper elevation={1} style={{ height: "100%" }}>
      <div className={styles.recentSourcesContainer}>
        <Typography variant="h6" display="inline">
          Recently Added Sources
        </Typography>
        <div style={{ display: "inline-block", float: "right" }}>
          <WidgetPrefsDialog
            formValues={recentSourcesPrefs}
            stateBranchName="recentSources"
            title="Recent Sources Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
        </div>
        <RecentSourcesList sources={recentSources} />
      </div>
    </Paper>
  );
};

export default RecentSources;

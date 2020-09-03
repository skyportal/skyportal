import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import { makeStyles } from "@material-ui/core/styles";
import DragHandleIcon from "@material-ui/icons/DragHandle";

import { ra_to_hours, dec_to_hours } from "../units";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import SourceQuickView from "./SourceQuickView";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  stampContainer: {
    display: "contents",
  },
  stamp: {
    transition: "transform 0.1s",
    width: "5em",
    height: "auto",
    display: "block",
    "&:hover": {
      transform: "scale(1.5)",
    },
  },
  recentSourceListContainer: {
    height: "calc(100% - 3rem)",
    overflowY: "scroll",
    marginTop: "0.625rem",
  },
  recentSourceList: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  recentSourceItem: {
    display: "flex",
    flexFlow: "row nowrap",
    alignItems: "center",
    padding: "0 0.625rem",
  },
  recentSourceInfo: {
    display: "flex",
    flexFlow: "column wrap",
    margin: "1rem 2rem",
  },
  recentSourceName: {
    fontSize: "1rem",
  },
  recentSourceTime: {
    color: "gray",
  },
  quickViewButton: {
    visibility: "hidden",
    display: "none",
  },
  recentSourceItemWithButton: {
    display: "flex",
    flexFlow: "column nowrap",
    justifyContent: "center",
    marginBottom: "1rem",
    marginLeft: "0.625rem",
    alignItems: "center",
    transition: "all 0.3s ease",
    "&:hover": {
      backgroundColor: "#ddd",
    },
    "&:hover $quickViewButton": {
      visibility: "visible",
      display: "block",
    },
  },
}));

const defaultPrefs = {
  maxNumSources: "5",
};

const RecentSourcesList = ({ sources, styles }) => {
  if (sources === undefined) {
    return <div>Loading recent sources...</div>;
  }

  if (sources.length === 0) {
    return <div>No recent sources available.</div>;
  }

  return (
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
  ),
  styles: PropTypes.shape(Object).isRequired,
};

RecentSourcesList.defaultProps = {
  sources: undefined,
};

const RecentSources = ({ classes }) => {
  const styles = useStyles();

  const { recentSources } = useSelector((state) => state.recentSources);
  const recentSourcesPrefs =
    useSelector((state) => state.profile.preferences.recentSources) ||
    defaultPrefs;
  console.log(recentSources);
  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <Typography variant="h6" display="inline">
          Recently Added Sources
        </Typography>
        <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        <div className={classes.widgetIcon}>
          <WidgetPrefsDialog
            formValues={recentSourcesPrefs}
            stateBranchName="recentSources"
            title="Recent Sources Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
        </div>
        <RecentSourcesList sources={recentSources} styles={styles} />
      </div>
    </Paper>
  );
};

RecentSources.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default RecentSources;

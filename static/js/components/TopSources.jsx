import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";

import { ra_to_hours, dec_to_hours } from "../units";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import { useSourceListStyles } from "./RecentSources";
import SourceQuickView from "./SourceQuickView";

const defaultPrefs = {
  maxNumSources: "",
  sinceDaysAgo: "",
};

const TopSourcesList = ({ sources, styles }) => {
  if (sources === undefined) {
    return <div>Loading top sources...</div>;
  }

  if (sources.length === 0) {
    return <div>No top sources available.</div>;
  }

  return (
    <div className={styles.sourceListContainer}>
      <ul className={styles.sourceList}>
        {sources.map((source) => {
          let topsourceName = `${source.obj_id}`;
          if (source.classifications.length > 0) {
            // Display the most recent non-zero probability class
            const filteredClasses = source.classifications.filter(
              (i) => i.probability > 0
            );
            const sortedClasses = filteredClasses.sort((a, b) =>
              a.modified < b.modified ? 1 : -1
            );

            topsourceName += ` (${sortedClasses[0].classification})`;
          }

          return (
            <li key={`topSources_${source.obj_id}`}>
              <div
                data-testid={`topSourceItem_${source.obj_id}`}
                className={styles.sourceItemWithButton}
              >
                <div className={styles.sourceItem}>
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
                  <div className={styles.sourceInfo}>
                    <span className={styles.sourceName}>
                      <Link to={`/source/${source.obj_id}`}>
                        {`${topsourceName}`}
                      </Link>
                    </span>
                    <span>
                      {`\u03B1, \u03B4: ${ra_to_hours(
                        source.ra
                      )} ${dec_to_hours(source.dec)}`}
                    </span>
                  </div>
                  <div className={styles.sourceTime}>
                    <span>
                      <em>{`${source.views} view(s)`}</em>
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

TopSourcesList.propTypes = {
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      obj_id: PropTypes.string.isRequired,
      ra: PropTypes.number,
      dec: PropTypes.number,
      views: PropTypes.number.isRequired,
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

TopSourcesList.defaultProps = {
  sources: undefined,
};

const TopSources = ({ classes }) => {
  const sourceListStyles = useSourceListStyles();
  const { sourceViews } = useSelector((state) => state.topSources);
  const topSourcesPrefs =
    useSelector((state) => state.profile.preferences.topSources) ||
    defaultPrefs;

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <Typography variant="h6" display="inline">
          Top Sources
        </Typography>
        <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        <div className={classes.widgetIcon}>
          <WidgetPrefsDialog
            formValues={topSourcesPrefs}
            stateBranchName="topSources"
            title="Top Sources Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
        </div>
        <TopSourcesList sources={sourceViews} styles={sourceListStyles} />
      </div>
    </Paper>
  );
};

TopSources.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default TopSources;

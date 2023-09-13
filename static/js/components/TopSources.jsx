import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import ButtonGroup from "@mui/material/ButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";

import makeStyles from "@mui/styles/makeStyles";
import Button from "./Button";

import { ra_to_hours, dec_to_dms } from "../units";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import { useSourceListStyles } from "./RecentSources";
import SourceQuickView from "./SourceQuickView";

const useStyles = makeStyles((theme) => ({
  header: {},
  timespanSelect: {
    display: "flex",
    width: "100%",
    justifyContent: "center",
    marginBottom: "0.5rem",
    "& .MuiButton-label": {
      color: theme.palette.text.secondary,
    },
    "& .MuiButtonGroup-root": {
      flexWrap: "wrap",
    },
  },
  sourceListContainer: {
    height: "calc(100% - 5rem)",
    overflowY: "auto",
    marginTop: "0.625rem",
    paddingTop: "0.625rem",
  },
  sourceInfo: {
    display: "flex",
    flexDirection: "row",
    margin: "10px",
    width: "100%",
  },
  sourceNameContainer: {
    display: "flex",
    flexDirection: "column",
  },
  sourceNameLink: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  quickViewContainer: {
    display: "flex",
    flexDirection: "column",
    width: "45%",
    alignItems: "center",
    justifyContent: "space-between",
  },
  quickViewButton: {
    minHeight: "30px",
    visibility: "hidden",
    textAlign: "center",
    display: "none",
  },
}));

const getStyles = (timespan, currentTimespan, theme) => ({
  fontWeight:
    timespan.label === currentTimespan.label
      ? theme.typography.fontWeightBold
      : theme.typography.fontWeightMedium,
});

const timespans = [
  { label: "DAY", sinceDaysAgo: "1", tooltip: "Past 24 hours" },
  { label: "WEEK", sinceDaysAgo: "7", tooltip: "Past 7 days" },
  { label: "MONTH", sinceDaysAgo: "30", tooltip: "Past 30 days" },
  { label: "6 MONTHS", sinceDaysAgo: "180", tooltip: "Past 180 days" },
  { label: "YEAR", sinceDaysAgo: "365", tooltip: "Past 365 days" },
];

const defaultPrefs = {
  maxNumSources: "10",
  sinceDaysAgo: "7",
};

const TopSourcesList = ({ sources, styles }) => {
  const [thumbnailIdxs, setThumbnailIdxs] = useState({});

  useEffect(() => {
    sources?.forEach((source) => {
      setThumbnailIdxs((prevState) => ({
        ...prevState,
        [source.obj_id]: 0,
      }));
    });
  }, [sources]);

  const topSourceSpecificStyles = useStyles();
  if (sources === undefined) {
    return <div>Loading top sources...</div>;
  }

  if (sources.length === 0) {
    return <div>No top sources available.</div>;
  }

  return (
    <div className={topSourceSpecificStyles.sourceListContainer}>
      <ul className={styles.sourceList}>
        {sources?.map((source) => {
          let topsourceName = `${source.obj_id}`;
          if (source.classifications.length > 0) {
            // Display the most recent non-zero probability class, and that isn't a ml classifier
            const filteredClasses = source.classifications?.filter(
              (i) => i.probability > 0 && i.ml === false
            );
            const sortedClasses = filteredClasses.sort((a, b) =>
              a.modified < b.modified ? 1 : -1
            );

            if (sortedClasses.length > 0) {
              topsourceName += ` (${sortedClasses[0].classification})`;
            }
          }

          const imgClasses = source.thumbnails[thumbnailIdxs[source.obj_id]]
            ?.is_grayscale
            ? `${styles.stamp} ${styles.inverted}`
            : `${styles.stamp}`;

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
                      className={imgClasses}
                      src={
                        source.thumbnails[thumbnailIdxs[source.obj_id]]
                          ?.public_url ||
                        "/static/images/currently_unavailable.png"
                      }
                      alt={source.obj_id}
                      onError={(e) => {
                        // avoid infinite loop
                        if (
                          thumbnailIdxs[source.obj_id] ===
                          source.thumbnails.length - 1
                        ) {
                          e.target.onerror = null;
                        }
                        setThumbnailIdxs((prevState) => ({
                          ...prevState,
                          [source.obj_id]: prevState[source.obj_id] + 1,
                        }));
                      }}
                    />
                  </Link>
                  <div className={styles.sourceInfo}>
                    <div className={styles.sourceNameContainer}>
                      <span className={styles.sourceName}>
                        <Link to={`/source/${source.obj_id}`}>
                          <span className={styles.sourceNameLink}>
                            {topsourceName}
                          </span>
                        </Link>
                      </span>
                      <span>
                        {`\u03B1, \u03B4: ${ra_to_hours(
                          source.ra
                        )} ${dec_to_dms(source.dec)}`}
                      </span>
                    </div>
                    <div className={styles.quickViewContainer}>
                      <span>
                        <em>{`${source.views} view(s)`}</em>
                      </span>
                      <SourceQuickView
                        sourceId={source.obj_id}
                        className={styles.quickViewButton}
                      />
                    </div>
                  </div>
                </div>
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
      thumbnails: PropTypes.arrayOf(
        PropTypes.shape({
          public_url: PropTypes.string,
          is_grayscale: PropTypes.bool,
          type: PropTypes.string,
        })
      ),
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
  const styles = useStyles();

  const invertThumbnails = useSelector(
    (state) => state.profile.preferences.invertThumbnails
  );
  const sourceListStyles = useSourceListStyles({ invertThumbnails });

  const { sourceViews } = useSelector((state) => state.topSources);
  const topSourcesPrefs =
    useSelector((state) => state.profile.preferences.topSources) ||
    defaultPrefs;

  if (!Object.keys(topSourcesPrefs).includes("maxNumSources")) {
    topSourcesPrefs.maxNumSources = defaultPrefs.maxNumSources;
  }

  const [currentTimespan, setCurrentTimespan] = useState(
    timespans.find(
      (timespan) => timespan.sinceDaysAgo === topSourcesPrefs.sinceDaysAgo
    )
  );
  const theme = useTheme();
  const dispatch = useDispatch();

  const switchTimespan = (event) => {
    const newTimespan = timespans.find(
      (timespan) => timespan.label === event.target.innerText
    );
    setCurrentTimespan(newTimespan);
    topSourcesPrefs.sinceDaysAgo = newTimespan.sinceDaysAgo;

    dispatch(
      profileActions.updateUserPreferences({ topSources: topSourcesPrefs })
    );
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" display="inline">
            Top Sources
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              // Only expose num sources
              initialValues={{ maxNumSources: topSourcesPrefs.maxNumSources }}
              stateBranchName="topSources"
              title="Top Sources Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.timespanSelect}>
          <ButtonGroup
            size="small"
            variant="text"
            aria-label="topSourcesTimespanSelect"
          >
            {timespans.map((timespan) => (
              <Tooltip key={timespan.label} title={timespan.tooltip}>
                <div>
                  <Button
                    onClick={switchTimespan}
                    style={getStyles(timespan, currentTimespan, theme)}
                    data-testid={`topSources_${timespan.sinceDaysAgo}days`}
                  >
                    {timespan.label}
                  </Button>
                </div>
              </Tooltip>
            ))}
          </ButtonGroup>
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

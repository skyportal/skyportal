import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import makeStyles from "@mui/styles/makeStyles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import Button from "./Button";

import { ra_to_hours, dec_to_dms } from "../units";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import { useSourceListStyles } from "./RecentSources";
import SourceQuickView from "./SourceQuickView";

const useStyles = makeStyles((theme) => ({
  header: {},
  timespanSelect: {
    display: "inline",
    "& > button": {
      height: "1.5rem",
      fontSize: "0.75rem",
      marginTop: "-0.2rem",
    },
  },
  timespanMenuItem: {
    fontWeight: "bold",
    fontSize: "0.75rem",
    height: "1.5rem",
    padding: "0.25rem 0.5rem",
  },
  sourceListContainer: {
    height: "calc(100% - 2.5rem)",
    overflowY: "auto",
  },
  sourceInfo: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    margin: "10px",
    marginRight: 0,
    width: "100%",
  },
  sourceNameContainer: {
    display: "flex",
    flexDirection: "column",
  },
  sourceName: {
    fontSize: "1rem",
    paddingBottom: 0,
    marginBottom: 0,
  },
  classification: {
    fontSize: "0.95rem",
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
    fontWeight: "bold",
    fontStyle: "italic",
    marginLeft: "-0.09rem",
    marginTop: "-0.4rem",
  },
  sourceCoordinates: {
    marginTop: "0.1rem",
    display: "flex",
    flexDirection: "column",
    "& > span": {
      marginTop: "-0.2rem",
    },
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
    alignItems: "flex-end",
    justifyContent: "space-between",
  },
  quickViewButton: {
    visibility: "hidden",
    textAlign: "center",
    display: "none",
  },
}));

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
          const topsourceName = `${source.obj_id}`;
          let classification = null;
          if (source.classifications.length > 0) {
            // Display the most recent non-zero probability class, and that isn't a ml classifier
            const filteredClasses = source.classifications?.filter(
              (i) => i.probability > 0 && i.ml === false,
            );
            const sortedClasses = filteredClasses.sort((a, b) =>
              a.modified < b.modified ? 1 : -1,
            );

            if (sortedClasses.length > 0) {
              classification = `(${sortedClasses[0].classification})`;
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
                      <Link
                        to={`/source/${source.obj_id}`}
                        className={styles.sourceName}
                      >
                        <span className={styles.sourceNameLink}>
                          {topsourceName}
                        </span>
                      </Link>
                      {classification && (
                        <span className={styles.classification}>
                          {classification}
                        </span>
                      )}
                      <div className={styles.sourceCoordinates}>
                        <span
                          style={{ fontSize: "0.95rem", whiteSpace: "pre" }}
                        >
                          {`\u03B1: ${ra_to_hours(source.ra)}`}
                        </span>
                        <span
                          style={{ fontSize: "0.95rem", whiteSpace: "pre" }}
                        >
                          {`\u03B4: ${dec_to_dms(source.dec)}`}
                        </span>
                      </div>
                    </div>
                    <div className={styles.quickViewContainer}>
                      <span style={{ textAlign: "right" }}>
                        <em>{`${source.views} view(s)`}</em>
                      </span>
                      <div
                        style={{
                          minHeight: "3rem",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-end",
                        }}
                      >
                        <SourceQuickView
                          sourceId={source.obj_id}
                          className={styles.quickViewButton}
                        />
                      </div>
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
        }),
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
        }),
      ),
    }),
  ),
  styles: PropTypes.shape(Object).isRequired,
};

TopSourcesList.defaultProps = {
  sources: undefined,
};

const TopSources = ({ classes }) => {
  const styles = useStyles();
  const dispatch = useDispatch();

  const invertThumbnails = useSelector(
    (state) => state.profile.preferences.invertThumbnails,
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
      (timespan) => timespan.sinceDaysAgo === topSourcesPrefs.sinceDaysAgo,
    ),
  );

  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const switchTimespan = (selectedTimespan) => {
    const newTimespan = timespans.find(
      (timespan) => timespan.label === selectedTimespan.label,
    );
    setCurrentTimespan(newTimespan);
    topSourcesPrefs.sinceDaysAgo = newTimespan.sinceDaysAgo;

    dispatch(
      profileActions.updateUserPreferences({ topSources: topSourcesPrefs }),
    );
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography
            variant="h6"
            display="inline"
            style={{ marginRight: "0.5rem" }}
          >
            Top Sources
          </Typography>
          <div className={styles.timespanSelect}>
            <Button
              variant="contained"
              aria-controls={open ? "basic-menu" : undefined}
              aria-haspopup="true"
              aria-expanded={open ? "true" : undefined}
              onClick={(e) => setAnchorEl(e.currentTarget)}
              size="small"
              endIcon={open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            >
              {currentTimespan.label}
            </Button>
            <Menu
              transitionDuration={50}
              id="finding-chart-menu"
              anchorEl={anchorEl}
              open={open}
              onClose={() => setAnchorEl(null)}
              MenuListProps={{
                "aria-labelledby": "basic-button",
              }}
            >
              {timespans.map((timespan) => (
                <MenuItem
                  className={styles.timespanMenuItem}
                  key={timespan.label}
                  onClick={() => {
                    switchTimespan(timespan);
                    setAnchorEl(null);
                  }}
                >
                  {timespan.label}
                </MenuItem>
              ))}
            </Menu>
          </div>
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

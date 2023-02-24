import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import makeStyles from "@mui/styles/makeStyles";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import CircularProgress from "@mui/material/CircularProgress";

import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import { showNotification } from "baselayer/components/Notifications";
import { ra_to_hours, dec_to_dms } from "../units";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import SourceQuickView from "./SourceQuickView";

import * as sourcesActions from "../ducks/sources";

dayjs.extend(relativeTime);
dayjs.extend(utc);

export const useSourceListStyles = makeStyles((theme) => ({
  stampContainer: {
    display: "contents",
  },
  stamp: () => ({
    transition: "transform 0.1s",
    width: "5em",
    height: "auto",
    display: "block",
    "&:hover": {
      color: "rgba(255, 255, 255, 1)",
      boxShadow: "0 5px 15px rgba(51, 52, 92, 0.6)",
    },
  }),
  inverted: ({ invertThumbnails }) => ({
    filter: invertThumbnails ? "invert(1)" : "unset",
    WebkitFilter: invertThumbnails ? "invert(1)" : "unset",
  }),
  sourceListContainer: {
    height: "calc(100% - 3rem)",
    overflowY: "auto",
    marginTop: "0.625rem",
    paddingTop: "0.625rem",
  },
  sourceList: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  sourceItem: {
    display: "flex",
    flexFlow: "row nowrap",
    alignItems: "center",
    padding: "0 0.625rem",
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
  sourceName: {
    fontSize: "1rem",
  },
  sourceNameLink: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  link: {
    color: theme.palette.warning.main,
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
  sourceItemWithButton: {
    display: "flex",
    flexFlow: "column nowrap",
    justifyContent: "center",
    // marginBottom: "1rem",
    transition: "all 0.3s ease",
    "&:hover": {
      backgroundColor:
        theme.palette.mode === "light" ? theme.palette.secondary.light : null,
    },
    "&:hover $quickViewButton": {
      visibility: "visible",
      display: "block",
    },
  },
  root: {
    "& .MuiOutlinedInput-root": {
      "& fieldset": {
        borderColor: "#333333",
      },
      "&:hover fieldset": {
        borderColor: "#333333",
      },
      "&.Mui-focused fieldset": {
        borderColor: "#333333",
      },
    },
  },
  textField: {
    color: "#333333",
  },
  icon: {
    color: "#333333",
  },
  paper: {
    backgroundColor: "#F0F8FF",
  },
  // These rules help keep the progress wheel centered. Taken from the first example: https://material-ui.com/components/progress/
  progress: {
    display: "flex",
    // The below color rule is not for the progress container, but for CircularProgress. This component only accepts 'primary', 'secondary', or 'inherit'.
    color: theme.palette.info.main,
    "& > * + *": {
      marginLeft: theme.spacing(2),
    },
  },
}));

const defaultPrefs = {
  maxNumSources: "5",
};

function containsSpecialCharacters(str) {
  /* eslint-disable-next-line no-useless-escape */
  const regex = /[ !@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/g;
  return regex.test(str);
}

const RecentSourcesSearchbar = ({ styles }) => {
  const [inputValue, setInputValue] = useState("");
  const [options] = useState([]);
  const [value] = useState(null);
  const [loading] = useState(false);
  const [open, setOpen] = useState(false);

  const classes = styles;

  const dispatch = useDispatch();
  const sourcesState = useSelector((state) => state.sources.latest);

  useEffect(() => {
    dispatch(sourcesActions.fetchSources());
  }, [dispatch]);

  let results = [];
  const handleChange = (e) => {
    e.preventDefault();
    const spec_char = containsSpecialCharacters(e.target.value);
    if (!spec_char) {
      setInputValue(e.target.value);
    } else {
      dispatch(showNotification("No special characters allowed", "error"));
      setInputValue([]);
    }
  };
  if (inputValue.length > 0) {
    results = sourcesState?.sources?.filter((source) =>
      source.id.toLowerCase().match(inputValue.toLowerCase())
    );
  }

  function formatSource(source) {
    if (source.id) {
      source.obj_id = source.id;
    }
  }

  const formattedResults = [];
  Object.assign(formattedResults, results);

  formattedResults.map(formatSource);

  return (
    <div>
      <Autocomplete
        color="primary"
        id="recent-sources-search-bar"
        style={{ padding: "0.3rem" }}
        classes={{ root: classes.root, paper: classes.paper }}
        isOptionEqualToValue={(option, val) => option.name === val.name}
        getOptionLabel={(option) => option}
        onInputChange={handleChange}
        onClose={() => setOpen(false)}
        size="small"
        noOptionsText="No matching sources."
        options={options}
        open={open}
        limitTags={15}
        value={value}
        popupIcon={null}
        renderInput={(params) => (
          <TextField
            // eslint-disable-next-line react/jsx-props-no-spreading
            {...params}
            variant="outlined"
            placeholder="Source"
            InputProps={{
              ...params.InputProps,
              className: classes.textField,
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" className={classes.icon} />
                </InputAdornment>
              ),
              endAdornment: (
                <div className={classes.progress}>
                  {loading ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : null}
                </div>
              ),
            }}
          />
        )}
      />
      {results?.length !== 0 && (
        <RecentSourcesList sources={formattedResults} styles={styles} search />
      )}
    </div>
  );
};

const RecentSourcesList = ({ sources, styles, search = false }) => {
  const [thumbnailIdxs, setThumbnailIdxs] = useState({});

  useEffect(() => {
    sources?.forEach((source) => {
      setThumbnailIdxs((prevState) => ({
        ...prevState,
        [source.obj_id]: 0,
      }));
    });
  }, [sources]);

  if (sources === undefined) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  if (sources.length === 0 && !search) {
    return <div>No recent sources available.</div>;
  }

  return (
    <div className={styles.sourceListContainer}>
      <ul className={styles.sourceList}>
        {sources.map((source) => {
          let recentSourceName = `${source.obj_id}`;
          if (source.classifications.length > 0) {
            // Display the most recent non-zero probability class
            const filteredClasses = source.classifications?.filter(
              (i) => i.probability > 0
            );
            const sortedClasses = filteredClasses.sort((a, b) =>
              a.modified < b.modified ? 1 : -1
            );

            if (sortedClasses.length > 0) {
              recentSourceName += ` (${sortedClasses[0].classification})`;
            }
          }

          const imgClasses = source.thumbnails[thumbnailIdxs[source.obj_id]]
            ?.is_grayscale
            ? `${styles.stamp} ${styles.inverted}`
            : `${styles.stamp}`;
          return (
            <li key={`recentSources_${source.obj_id}_${source.created_at}`}>
              <div
                data-testid={`recentSourceItem_${source.obj_id}_${source.created_at}`}
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
                      loading="lazy"
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
                            {recentSourceName}
                          </span>
                        </Link>
                      </span>
                      <span>
                        {`\u03B1, \u03B4: ${ra_to_hours(
                          source.ra
                        )} ${dec_to_dms(source.dec)}`}
                      </span>
                      {source.resaved && <span>(Source was re-saved)</span>}
                    </div>
                    <div className={styles.quickViewContainer}>
                      <span>
                        {dayjs().to(dayjs.utc(`${source.created_at}Z`))}
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

RecentSourcesList.propTypes = {
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      obj_id: PropTypes.string.isRequired,
      ra: PropTypes.number,
      dec: PropTypes.number,
      created_at: PropTypes.string.isRequired,
      thumbnails: PropTypes.arrayOf(
        PropTypes.shape({
          public_url: PropTypes.string,
          is_grayscale: PropTypes.bool,
          type: PropTypes.string,
        })
      ),
      resaved: PropTypes.bool,
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
  search: PropTypes.bool,
};

RecentSourcesList.defaultProps = {
  sources: undefined,
  search: false,
};

const RecentSources = ({ classes }) => {
  const invertThumbnails = useSelector(
    (state) => state.profile.preferences.invertThumbnails
  );
  const styles = useSourceListStyles({ invertThumbnails });

  const { recentSources } = useSelector((state) => state.recentSources);
  const recentSourcesPrefs =
    useSelector((state) => state.profile.preferences.recentSources) ||
    defaultPrefs;

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography variant="h6" display="inline">
            Recently Saved Sources
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              initialValues={recentSourcesPrefs}
              stateBranchName="recentSources"
              title="Recent Sources Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
          <Paper>
            <RecentSourcesSearchbar styles={styles} />
          </Paper>
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

RecentSourcesSearchbar.propTypes = {
  recentSources: PropTypes.arrayOf(
    PropTypes.shape({
      obj_id: PropTypes.string.isRequired,
      ra: PropTypes.number,
      dec: PropTypes.number,
      created_at: PropTypes.string.isRequired,
      thumbnails: PropTypes.arrayOf(
        PropTypes.shape({
          public_url: PropTypes.string,
          is_grayscale: PropTypes.bool,
          type: PropTypes.string,
        })
      ),
      resaved: PropTypes.bool,
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
  filter: PropTypes.func.isRequired,
};

RecentSourcesSearchbar.defaultProps = {
  recentSources: undefined,
};

export default RecentSources;

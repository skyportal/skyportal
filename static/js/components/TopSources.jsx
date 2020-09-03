import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";

import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

import styles from "./TopSources.css";

const defaultPrefs = {
  maxNumSources: "",
  sinceDaysAgo: "",
};

const TopSources = ({ classes }) => {
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
        <p>Displaying most-viewed sources</p>
        <ul className={styles.topSourceList}>
          {sourceViews.map(({ obj_id, views, public_url }) => (
            <li
              key={`topSources_${obj_id}_${views}`}
              className={styles.topSource}
            >
              <Link to={`/source/${obj_id}`}>
                <img className={styles.stamp} src={public_url} alt={obj_id} />
              </Link>
              <span>
                {" - "}
                <Link to={`/source/${obj_id}`}>{obj_id}</Link>
              </span>
              <span>
                <em>{` - ${views} view(s)`}</em>
              </span>
            </li>
          ))}
        </ul>
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

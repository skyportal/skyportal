import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import { CountUp } from "use-count-up";

import { makeStyles } from "@material-ui/core/styles";
import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import * as profileActions from "../ducks/profile";

const defaultPrefs = {
  sinceDaysAgo: "",
};

const useStyles = makeStyles(() => ({
  counter: {
    display: "inline-block",
    align: "center",
  },
}));

const SourceCounts = ({ classes }) => {
  const styles = useStyles();
  const sourceCounts = useSelector((state) => state.sourceCounts.sourceCounts);
  const sourceCountPrefs =
    useSelector((state) => state.profile.preferences.sourceCounts) ||
    defaultPrefs;

  return (
    <Paper id="sourceCountsWidget" elevation={1}>
      <div className={classes.widgetPaperDiv}>
        <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        <div className={classes.widgetIcon}>
          <WidgetPrefsDialog
            formValues={sourceCountPrefs}
            stateBranchName="sourceCounts"
            title="Source Count Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
        </div>
        <div className={styles.counter}>
          <Typography align="center" variant="h4">
            <b>
              <CountUp
                id="sourceCounter"
                isCounting
                end={sourceCounts?.count}
                duration={1.0}
              />
            </b>
          </Typography>
          <Typography align="center" variant="body1">
            New Sources <br />
            <i>Last {sourceCounts?.since_days_ago} days</i>
          </Typography>
        </div>
      </div>
    </Paper>
  );
};

SourceCounts.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
  }).isRequired,
};

export default SourceCounts;

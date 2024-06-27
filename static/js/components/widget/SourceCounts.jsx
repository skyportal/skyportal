import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import { CountUp } from "use-count-up";

import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import * as profileActions from "../../ducks/profile";

const useStyles = makeStyles(() => ({
  counter: {
    width: "100%",
    display: "flex",
    flexDirection: "column",
    paddingTop: "2rem",
    height: "100%",
    justifyContent: "center",
  },
  widgetsBar: {
    position: "fixed",
    right: "1rem",
    zIndex: 1,
  },
}));

const SourceCounts = ({ classes, sinceDaysAgo }) => {
  const styles = useStyles();
  const sourceCounts = useSelector((state) => state.sourceCounts?.sourceCounts);
  const userPrefs = useSelector(
    (state) => state.profile.preferences.sourceCounts,
  );

  const defaultPrefs = {
    sinceDaysAgo: sinceDaysAgo ? sinceDaysAgo.toString() : "",
  };
  const sourceCountPrefs = userPrefs || defaultPrefs;

  return (
    <Paper
      id="sourceCountsWidget"
      elevation={1}
      className={classes.widgetPaperFillSpace}
    >
      <div className={classes.widgetPaperDiv}>
        <div className={styles.widgetsBar}>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              initialValues={sourceCountPrefs}
              stateBranchName="sourceCounts"
              title="Source Count Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
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
            <i>Last {sourceCounts?.sinceDaysAgo} days</i>
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
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
  sinceDaysAgo: PropTypes.number,
};

SourceCounts.defaultProps = {
  sinceDaysAgo: undefined,
};
export default SourceCounts;

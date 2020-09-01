import React from "react";
import { useSelector } from "react-redux";
import { CountUp } from "use-count-up";
import { makeStyles } from "@material-ui/core/styles";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import * as profileActions from "../ducks/profile";

const defaultPrefs = {
  sinceDaysAgo: "",
};

const useStyles = makeStyles(() => ({
  prefwidget: {
    display: "inline-block",
    float: "right",
  },
  counter: {
    display: "inline-block",
    align: "center",
  },
  counterContainer: {
    display: "block",
    padding: "1rem",
    height: "100%",
  },
}));

const SourceCounts = () => {
  const classes = useStyles();
  const sourceCounts = useSelector((state) => state.sourceCounts.sourceCounts);
  const sourceCountPrefs =
    useSelector((state) => state.profile.preferences.sourceCounts) ||
    defaultPrefs;

  return (
    <Paper id="sourceCounts" elevation={1}>
      <div className={classes.counterContainer}>
        <div className={classes.prefwidget}>
          <WidgetPrefsDialog
            formValues={sourceCountPrefs}
            stateBranchName="sourceCounts"
            title="Source Count Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
        </div>
        <div className={classes.counter}>
          <Typography align="center" variant="h4">
            <b>
              <CountUp isCounting end={sourceCounts?.count} duration={2.5} />
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

export default SourceCounts;

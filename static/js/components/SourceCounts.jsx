import React from "react";
import { useSelector } from "react-redux";
import { CountUp } from "use-count-up";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import * as profileActions from "../ducks/profile";

import styles from "./TopSources.css";

const defaultPrefs = {
  sinceDaysAgo: "",
};

const SourceCounts = () => {
  const sourceCounts = useSelector((state) => state.sourceCounts.sourceCounts);
  const sourceCountPrefs =
    useSelector((state) => state.profile.preferences.sourceCounts) ||
    defaultPrefs;

  return (
    <Paper elevation={1}>
      <div className={styles.topSourcesContainer}>
        <div style={{ display: "inline-block", float: "right" }}>
          <WidgetPrefsDialog
            formValues={sourceCountPrefs}
            stateBranchName="sourceCounts"
            title="Source Count Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
        </div>
        <div style={{ display: "inline-block", align: "center" }}>
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

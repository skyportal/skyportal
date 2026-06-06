import { CountUp } from "use-count-up";

import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetSourceCountsQuery } from "../../ducks/sourceCounts";

const useStyles = makeStyles()(() => ({
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

interface SourceCountsProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
  sinceDaysAgo?: number;
}

const SourceCounts = ({ classes, sinceDaysAgo }: SourceCountsProps) => {
  const { classes: styles } = useStyles();
  const { data: sourceCounts } = useGetSourceCountsQuery();
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const userPrefs = (profile?.preferences as any)?.sourceCounts;

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
              onSubmit={updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.counter}>
          <Typography align="center" variant="h4">
            <b>
              <CountUp
                {...({ id: "sourceCounter" } as any)}
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

export default SourceCounts;

import React, { useState } from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import CircularProgress from "@material-ui/core/CircularProgress";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";

import { observingRunTitle } from "./AssignmentForm";
import NewObservingRun from "./NewObservingRun";

dayjs.extend(utc);
dayjs.extend(duration);
dayjs.extend(relativeTime);

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
}));

export function observingRunInfo(observingRun, instrumentList, telescopeList) {
  const { instrument_id } = observingRun;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(observingRun?.calendar_date && instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const nowDate = dayjs().utc();
  const runDate = dayjs(observingRun?.calendar_date);
  const dt = dayjs.duration(runDate.diff(nowDate));

  const result = dt.humanize(true);

  return result;
}

const ObservingRunList = ({ observingRuns }) => {
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const nowDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const dt_month = dayjs.duration(1, "month");

  const [displayAll, setDisplayAll] = useState(false);

  const toggleCheckbox = () => {
    setChecked(!checked);
  };

  let observingRunsToShow = [];
  if (!checked) {
    observingRuns?.forEach((run) => {
      const dt = dayjs.duration(dayjs(run.calendar_date).diff(nowDate));
      if (dt.$ms < dt_month.$ms && dt.$ms > 0) {
        observingRunsToShow.push(run);
      }
    });
  } else {
    observingRunsToShow = [...observingRuns];
  }

  return (
    <div className={classes.root}>
      <List component="nav">
        {observingRunsToShow?.map((run) => (
          <ListItem button component={Link} to={`/run/${run.id}`} key={run.id}>
            <ListItemText
              primary={observingRunTitle(
                run,
                instrumentList,
                telescopeList,
                groups
              )}
              secondary={observingRunInfo(run, instrumentList, telescopeList)}
            />
          </ListItem>
        ))}
        <input
          type="checkbox"
          onChange={toggleCheckbox}
          name="observationRun"
          data-testid="observationRunCheckbox"
        />
        Display all observing runs? &nbsp;&nbsp;
      </List>
    </div>
  );
};

const ObservingRunPage = () => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Observing Runs</Typography>
            <ObservingRunList observingRuns={observingRunList} />
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Add a New Observing Run</Typography>
            <NewObservingRun />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

ObservingRunList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  observingRuns: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default ObservingRunPage;

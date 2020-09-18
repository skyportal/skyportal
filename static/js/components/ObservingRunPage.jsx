import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import PropTypes from "prop-types";
import { observingRunTitle } from "./AssignmentForm";
import NewObservingRun from "./NewObservingRun";

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

const ObservingRunList = ({ observingRuns }) => {
  const classes = useStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  return (
    <div className={classes.root}>
      <List component="nav">
        {observingRuns.map((run) => (
          <ListItem button component={Link} to={`/run/${run.id}`} key={run.id}>
            <ListItemText
              primary={observingRunTitle(
                run,
                instrumentList,
                telescopeList,
                groups
              )}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const ObservingRunPage = () => {
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Observing Runs</Typography>
            <ObservingRunList observingRuns={observingRunList} />
          </div>
        </Paper>
      </Grid>
      <Grid item xs={12} md={6} sm={12}>
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
  observingRuns: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default ObservingRunPage;

import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";

import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";

import SourceListFilterForm from "./SourceListFilterForm";
import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import SourceTable from "./SourceTable";

const useStyles = makeStyles(() => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  tableGrid: {
    width: "100%",
  },
}));

const SourceList = () => {
  const classes = useStyles();
  const sources = useSelector((state) => state.sources);
  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  const dispatch = useDispatch();

  useEffect(() => {
    if (!sources.latest) {
      dispatch(sourcesActions.fetchSources());
    }
  }, [sources.latest, dispatch]);

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }
  if (sources.latest) {
    return (
      <Paper elevation={1}>
        <div className={classes.paperDiv}>
          <Typography variant="h6" display="inline">
            Sources
          </Typography>
          <SourceListFilterForm sources={sources} />
          {!sources.queryInProgress && (
            <Grid item className={classes.tableGrid}>
              <SourceTable sources={sources.latest} />
            </Grid>
          )}
          {sources.queryInProgress && (
            <div>
              <br />
              <br />
              <i>Query in progress...</i>
            </div>
          )}
        </div>
      </Paper>
    );
  }
  return <div>Loading sources...</div>;
};

export default SourceList;

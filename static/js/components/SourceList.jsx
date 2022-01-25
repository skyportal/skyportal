import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import Paper from "@material-ui/core/Paper";
import { makeStyles } from "@material-ui/core/styles";
import Grid from "@material-ui/core/Grid";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";

import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import SourceTable from "./SourceTable";

const useStyles = makeStyles((theme) => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  tableGrid: {
    width: "100%",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  paper: {
    padding: "1rem",
    marginTop: "0.625rem",
  },
  root: {
    display: "flex",
    flexWrap: "wrap",
    "& .MuiTextField-root": {
      margin: theme.spacing(0.2),
      width: "10rem",
    },
  },
  blockWrapper: {
    width: "100%",
    marginBottom: "0.5rem",
  },
  title: {
    margin: "0.5rem 0rem 0rem 0rem",
  },
  spinner: {
    marginTop: "1rem",
    marginLeft: "auto",
    marginRight: "auto",
    display: "flex",
    top: "50%",
    left: "50%",
    position: "fixed",
  },
}));

const SourceList = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const sourcesState = useSelector((state) => state.sources.latest);
  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  const [rowsPerPage, setRowsPerPage] = useState(100);

  useEffect(() => {
    dispatch(sourcesActions.fetchSources());
  }, [dispatch]);

  const handleSourceTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData
  ) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchSources(data));
  };

  const handleSourceTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(sourcesActions.fetchSources(data));
  };

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }
  if (!sourcesState.sources) {
    return <CircularProgress className={classes.spinner} />;
  }

  return (
    <Paper elevation={1} className={classes.paper}>
      <div className={classes.paperDiv}>
        <Typography variant="h6" display="inline">
          Sources
        </Typography>
        {sourcesState.sources && (
          <Grid item className={classes.tableGrid}>
            <SourceTable
              sources={sourcesState.sources}
              paginateCallback={handleSourceTablePagination}
              totalMatches={sourcesState.totalMatches}
              pageNumber={sourcesState.pageNumber}
              numPerPage={sourcesState.numPerPage}
              sortingCallback={handleSourceTableSorting}
            />
          </Grid>
        )}
        {!sourcesState.sources && (
          <CircularProgress className={classes.spinner} />
        )}
      </div>
    </Paper>
  );
};

export default SourceList;

import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import Paper from "@mui/material/Paper";
import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import InstrumentTable from "./InstrumentTable";
import Spinner from "./Spinner";
import * as instrumentsActions from "../ducks/instruments";

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
}));

const InstrumentList = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);

  const [rowsPerPage, setRowsPerPage] = useState(100);

  useEffect(() => {
    dispatch(instrumentsActions.fetchInstruments());
  }, [dispatch]);

  const handleInstrumentTablePagination = (
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
    dispatch(instrumentsActions.fetchInstruments(data));
  };

  const handleInstrumentTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(instrumentsActions.fetchInstruments(data));
  };

  if (!instrumentsState.instrumentList) {
    return <Spinner />;
  }

  return (
    <Paper elevation={1} className={classes.paper}>
      <div className={classes.paperDiv}>
        <Typography variant="h6" display="inline">
          Instruments
        </Typography>
        {instrumentsState.instrumentList && (
          <Grid item className={classes.tableGrid}>
            <InstrumentTable
              instruments={instrumentsState.instrumentList}
              telescopes={telescopesState.telescopeList}
              paginateCallback={handleInstrumentTablePagination}
              totalMatches={instrumentsState.totalMatches}
              pageNumber={instrumentsState.pageNumber}
              numPerPage={instrumentsState.numPerPage}
              sortingCallback={handleInstrumentTableSorting}
            />
          </Grid>
        )}
        {!instrumentsState.instrumentList && <Spinner />}
      </div>
    </Paper>
  );
};

export default InstrumentList;

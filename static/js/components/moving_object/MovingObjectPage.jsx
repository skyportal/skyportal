import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Paper from "@mui/material/Paper";
import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

import MovingObjectTable from "./MovingObjectTable";
import Spinner from "../Spinner";
import * as movingObjectsActions from "../../ducks/moving_objects";

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
  movingObjectDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  movingObjectDeleteDisabled: {
    opacity: 0,
  },
}));

const MovingObjectPage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { movingObjects } = useSelector((state) => state.moving_objects);

  const [rowsPerPage, setRowsPerPage] = useState(100);

  useEffect(() => {
    dispatch(movingObjectsActions.fetchMovingObjects());
  }, [dispatch]);

  const handleMovingObjectTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
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
    dispatch(movingObjectsActions.fetchMovingObjects(data));
  };

  const handleMovingObjectTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(movingObjectsActions.fetchMovingObjects(data));
  };

  if (!movingObjects) {
    return <Spinner />;
  }

  return (
    <Grid container spacing={2}>
      <Grid item md={12} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paper}>
            <Typography variant="h6" display="inline">
              Moving Objects
            </Typography>
            {typeof movingObjects?.moving_objects !== "undefined" && (
              <MovingObjectTable
                movingObjects={movingObjects?.moving_objects || []}
                paginateCallback={handleMovingObjectTablePagination}
                totalMatches={movingObjects?.totalMatches || 0}
                pageNumber={movingObjects?.pageNumber || 1}
                numPerPage={movingObjects?.numPerPage || 10}
                sortingCallback={handleMovingObjectTableSorting}
              />
            )}
          </div>
        </Paper>
      </Grid>
      {!movingObjects && <Spinner />}
    </Grid>
  );
};

export default MovingObjectPage;

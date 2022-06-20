import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";

import GalaxyTable from "./GalaxyTable";
import NewGalaxy from "./NewGalaxy";

import * as galaxiesActions from "../ducks/galaxies";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  header: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  content: {
    margin: "1rem",
  },
  paperContent: {
    padding: "1rem",
    marginBottom: "1rem",
  },
  dividerHeader: {
    background: theme.palette.primary.main,
    height: "2px",
  },
  divider: {
    background: theme.palette.secondary.main,
  },
}));

const defaultNumPerPage = 10;

const GalaxyPage = () => {
  const galaxies = useSelector((state) => state.galaxies?.galaxies);
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();
  const classes = useStyles();

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    dispatch(galaxiesActions.fetchGalaxies());
  }, [dispatch]);

  if (!galaxies) {
    return <p>No galaxies available...</p>;
  }

  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(galaxiesActions.fetchGalaxies(params));
  };

  const handleTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handlePageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h5">List of Galaxies</Typography>
            <GalaxyTable
              galaxies={galaxies.galaxies}
              pageNumber={fetchParams.pageNumber}
              numPerPage={fetchParams.numPerPage}
              handleTableChange={handleTableChange}
              totalMatches={galaxies.totalMatches}
            />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h5">Add New Galaxies</Typography>
              <NewGalaxy />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default GalaxyPage;

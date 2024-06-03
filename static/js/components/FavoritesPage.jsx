import React, { useEffect, useState } from "react";

import { useDispatch, useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";

import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import SourceTable from "./source/SourceTable";

import * as sourcesActions from "../ducks/sources";

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  source: {},
  commentListContainer: {
    height: "15rem",
    overflowY: "scroll",
    padding: "0.5rem 0",
  },
  tableGrid: {
    width: "100%",
  },
}));

const FavoritesPage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);

  useEffect(() => {
    dispatch(sourcesActions.fetchFavoriteSources());
  }, [dispatch]);

  const sourcesState = useSelector((state) => state.sources.favorites);

  const handleSourcesTableSorting = (sortData, filterData) => {
    dispatch(
      sourcesActions.fetchFavoriteSources({
        ...filterData,
        pageNumber: 1,
        numPerPage: sourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      }),
    );
  };

  const handleSourcesTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
  ) => {
    setSourcesRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchFavoriteSources(data));
  };

  if (sourcesState == null) {
    return <CircularProgress />;
  }

  if (sourcesState.sources.length === 0) {
    return (
      <div className={classes.source}>
        <Typography variant="h4" gutterBottom align="center">
          Favorite sources
        </Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources have been saved as favorites.
        </Typography>
      </div>
    );
  }

  return (
    <div className={classes.source}>
      {!!sourcesState.sources && (
        <SourceTable
          sources={sourcesState.sources}
          title="Favorite sources"
          paginateCallback={handleSourcesTablePagination}
          pageNumber={sourcesState.pageNumber}
          totalMatches={sourcesState.totalMatches}
          numPerPage={sourcesState.numPerPage}
          sortingCallback={handleSourcesTableSorting}
          favoritesRemoveButton
        />
      )}
    </div>
  );
};

export default FavoritesPage;

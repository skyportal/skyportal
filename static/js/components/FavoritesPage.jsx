import React, { useEffect, useState } from "react";

import { useSelector, useDispatch } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";

import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import SourceTable from "./SourceTable";

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
  const sourcesState = useSelector((state) => state.sources.favorites);

  useEffect(() => {
    dispatch(sourcesActions.fetchFavoriteSources());
  }, [dispatch]);

  const handleSourcesTableSorting = (sortData) => {
    dispatch(
      sourcesActions.fetchFavoriteSources({
        pageNumber: 1,
        numPerPage: sourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      })
    );
  };

  const handleSourcesTablePagination = (pageNumber, numPerPage, sortData) => {
    setSourcesRowsPerPage(numPerPage);
    const data = {
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchFavoriteSources(data));
  };
  if (!sourcesState.sources) {
    return <CircularProgress />;
  }

  if (sourcesState.sources?.length === 0) {
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
      <Typography variant="h4" gutterBottom align="center">
        Favorite sources
      </Typography>

      {!!sourcesState.sources && (
        <SourceTable
          sources={sourcesState.sources}
          title="Favorites"
          paginateCallback={handleSourcesTablePagination}
          pageNumber={sourcesState.pageNumber}
          totalMatches={sourcesState.totalMatches}
          numPerPage={sourcesState.numPerPage}
          sortingCallback={handleSourcesTableSorting}
        />
      )}
    </div>
  );
};

export default FavoritesPage;

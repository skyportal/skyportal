import { useState } from "react";

import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import SourceTable from "../source/SourceTable";

import { useFetchFavoriteSourcesQuery } from "../../ducks/sources";

const useStyles = makeStyles()((theme) => ({
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
  const { classes } = useStyles();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);
  const [queryParams, setQueryParams] = useState<any>({});

  const { data: sourcesState } = useFetchFavoriteSourcesQuery(queryParams);

  const handleSourcesTableSorting = (sortData: any, filterData: any) => {
    setQueryParams({
      ...filterData,
      pageNumber: 1,
      numPerPage: sourcesRowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    });
  };

  const handleSourcesTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setSourcesRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    setQueryParams(data);
  };

  if (sourcesState == null) {
    return <CircularProgress />;
  }

  if (!sourcesState.sources || sourcesState.sources.length === 0) {
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
        />
      )}
    </div>
  );
};

export default FavoritesPage;

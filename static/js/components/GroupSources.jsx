import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
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

const GroupSources = ({ route }) => {
  const dispatch = useDispatch();
  const savedSourcesState = useSelector(
    (state) => state.sources.savedGroupSources
  );
  const pendingSourcesState = useSelector(
    (state) => state.sources.pendingGroupSources
  );
  const groups = useSelector((state) => state.groups.userAccessible);
  const classes = useStyles();
  const [savedSourcesRowsPerPage, setSavedSourcesRowsPerPage] = useState(10);
  const [pendingSourcesRowsPerPage, setPendingSourcesRowsPerPage] = useState(
    10
  );

  // Load the group sources
  useEffect(() => {
    dispatch(
      sourcesActions.fetchSavedGroupSources({
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: 10,
      })
    );
    dispatch(
      sourcesActions.fetchPendingGroupSources({
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: 10,
      })
    );
  }, [route.id, dispatch]);

  if (!savedSourcesState.sources && !pendingSourcesState.sources) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const groupID = parseInt(route.id, 10);

  const groupName = groups.filter((g) => g.id === groupID)[0]?.name || "";

  const handleSavedSourcesTableSorting = (sortData) => {
    dispatch(
      sourcesActions.fetchSavedGroupSources({
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: savedSourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      })
    );
  };

  const handleSavedSourcesTablePagination = (
    pageNumber,
    numPerPage,
    sortData
  ) => {
    setSavedSourcesRowsPerPage(numPerPage);
    const data = {
      group_ids: [route.id],
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchSavedGroupSources(data));
  };

  const handlePendingSourcesTableSorting = (sortData) => {
    dispatch(
      sourcesActions.fetchPendingGroupSources({
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: pendingSourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      })
    );
  };

  const handlePendingSourcesTablePagination = (
    pageNumber,
    numPerPage,
    sortData
  ) => {
    setPendingSourcesRowsPerPage(numPerPage);
    const data = {
      group_ids: [route.id],
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchPendingGroupSources(data));
  };

  return (
    <div className={classes.source}>
      <Typography variant="h4" gutterBottom align="center">
        {`${groupName} sources`}
      </Typography>
      <br />
      {!!savedSourcesState.sources && (
        <SourceTable
          sources={savedSourcesState.sources}
          title="Saved"
          sourceStatus="saved"
          groupID={groupID}
          paginateCallback={handleSavedSourcesTablePagination}
          pageNumber={savedSourcesState.pageNumber}
          totalMatches={savedSourcesState.totalMatches}
          numPerPage={savedSourcesState.numPerPage}
          sortingCallback={handleSavedSourcesTableSorting}
        />
      )}
      <br />
      <br />
      {!!pendingSourcesState.sources && (
        <SourceTable
          sources={pendingSourcesState.sources}
          title="Requested to save"
          sourceStatus="requested"
          groupID={groupID}
          paginateCallback={handlePendingSourcesTablePagination}
          pageNumber={pendingSourcesState.pageNumber}
          totalMatches={pendingSourcesState.totalMatches}
          numPerPage={pendingSourcesState.numPerPage}
          sortingCallback={handlePendingSourcesTableSorting}
        />
      )}
    </div>
  );
};

GroupSources.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default GroupSources;

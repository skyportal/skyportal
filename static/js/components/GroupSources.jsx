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

  const handleSavedSourcesTableSorting = (formData) => {
    dispatch(
      sourcesActions.fetchSavedGroupSources({
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: savedSourcesRowsPerPage,
        sortBy: formData.column,
        sortOrder: formData.ascending ? "asc" : "desc",
      })
    );
  };

  const handleSavedSourcesTablePagination = (pageNumber, numPerPage) => {
    setSavedSourcesRowsPerPage(numPerPage);
    dispatch(
      sourcesActions.fetchSavedGroupSources({
        group_ids: [route.id],
        pageNumber,
        numPerPage,
      })
    );
  };

  const handlePendingSourcesTableSorting = (formData) => {
    dispatch(
      sourcesActions.fetchPendingGroupSources({
        group_ids: [route.id],
        pageNumber: 1,
        numPerPage: pendingSourcesRowsPerPage,
        sortBy: formData.column,
        sortOrder: formData.ascending ? "asc" : "desc",
      })
    );
  };

  const handlePendingSourcesTablePagination = (pageNumber, numPerPage) => {
    setPendingSourcesRowsPerPage(numPerPage);
    dispatch(
      sourcesActions.fetchPendingGroupSources({
        group_ids: [route.id],
        pageNumber,
        numPerPage,
      })
    );
  };

  if (
    savedSourcesState.sources?.length === 0 &&
    pendingSourcesState.sources?.length === 0
  ) {
    return (
      <div className={classes.source}>
        <Typography variant="h4" gutterBottom align="center">
          {`${groupName} sources`}
        </Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources have been saved to this group yet.
        </Typography>
      </div>
    );
  }

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

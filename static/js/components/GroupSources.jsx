import React, { useEffect } from "react";
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
  const savedSources = useSelector((state) => state.sources.savedGroupSources);
  const pendingSources = useSelector(
    (state) => state.sources.pendingGroupSources
  );
  const groups = useSelector((state) => state.groups.userAccessible);
  const classes = useStyles();

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

  if (!savedSources && !pendingSources) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const groupID = parseInt(route.id, 10);

  const groupName = groups.filter((g) => g.id === groupID)[0]?.name || "";

  const handleSavedSourcesTablePagination = (pageNumber, numPerPage) => {
    dispatch(
      sourcesActions.fetchSavedGroupSources({
        group_ids: [route.id],
        pageNumber,
        numPerPage,
      })
    );
  };

  const handlePendingSourcesTablePagination = (pageNumber, numPerPage) => {
    dispatch(
      sourcesActions.fetchPendingGroupSources({
        group_ids: [route.id],
        pageNumber,
        numPerPage,
      })
    );
  };

  if (savedSources.length === 0 && pendingSources.length === 0) {
    return (
      <div className={classes.source}>
        <Typography variant="h4" gutterBottom align="center">
          {`${groupName} sources`}
        </Typography>
        <br />
        <Typography align="center">
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
      {savedSources && (
        <SourceTable
          sources={savedSources}
          title="Saved"
          sourceStatus="saved"
          groupID={groupID}
          paginateCallback={handleSavedSourcesTablePagination}
        />
      )}
      <br />
      <br />
      {pendingSources && (
        <SourceTable
          sources={pendingSources}
          title="Requested to save"
          sourceStatus="requested"
          groupID={groupID}
          paginateCallback={handlePendingSourcesTablePagination}
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

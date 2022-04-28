import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import CircularProgress from "@material-ui/core/CircularProgress";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import { makeStyles } from "@material-ui/core/styles";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";

import * as followupRequestActions from "../ducks/followup_requests";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
}));

const defaultNumPerPage = 10;

const FollowupRequestPage = () => {
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { followupRequestList, totalMatches } = useSelector(
    (state) => state.followup_requests
  );
  const classes = useStyles();
  const dispatch = useDispatch();

  const [queryInProgress, setQueryInProgress] = useState(false);
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    dispatch(followupRequestActions.fetchFollowupRequests());
  }, [dispatch]);

  const handlePageChange = async (page, numPerPage) => {
    setQueryInProgress(true);
    const params = { ...fetchParams, numPerPage, pageNumber: page + 1 };
    // Save state for future
    setFetchParams(params);
    await dispatch(followupRequestActions.fetchFollowupRequests(params));
    setQueryInProgress(false);
  };

  const handleTableChange = (action, tableState) => {
    if (action === "changePage") {
      handlePageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Followup Requests</Typography>
            {queryInProgress ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <FollowupRequestLists
                followupRequests={followupRequestList}
                instrumentList={instrumentList}
                instrumentFormParams={instrumentFormParams}
                pageNumber={fetchParams.pageNumber}
                numPerPage={fetchParams.numPerPage}
                handleTableChange={handleTableChange}
                totalMatches={totalMatches}
                serverSide
                showObject
              />
            )}
          </div>
        </Paper>
      </Grid>
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Filter Followup Requests</Typography>
            <FollowupRequestSelectionForm />
          </div>
        </Paper>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Prioritize Followup Requests</Typography>
            <FollowupRequestPrioritizationForm />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default FollowupRequestPage;

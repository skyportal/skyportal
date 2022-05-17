import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import Grid from "@material-ui/core/Grid";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";

import * as followupRequestActions from "../ducks/followup_requests";
import * as instrumentActions from "../ducks/instruments";

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
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { followupRequestList, totalMatches } = useSelector(
    (state) => state.followup_requests
  );
  const classes = useStyles();
  const dispatch = useDispatch();

  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(instrumentActions.fetchInstruments());

      const { data } = result;
      setSelectedInstrumentId(data[0]?.id);
    };

    getInstruments();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId]);

  useEffect(() => {
    const params = {
      ...fetchParams,
      numPerPage: defaultNumPerPage,
      pageNumber: 1,
      instrumentID: selectedInstrumentId,
    };
    dispatch(followupRequestActions.fetchFollowupRequests(params));
  }, [dispatch, selectedInstrumentId]);

  if (!Array.isArray(followupRequestList)) {
    return <p>Waiting for followup requests to load...</p>;
  }

  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
      instrumentID: selectedInstrumentId,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(followupRequestActions.fetchFollowupRequests(params));
  };

  const handleTableChange = (action, tableState) => {
    if (action === "changePage") {
      handlePageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    !selectedInstrumentId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>Loading information...</p>;
  }

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const requestsGroupedByInstId = followupRequestList.reduce((r, a) => {
    r[a.allocation.instrument.id] = [
      ...(r[a.allocation.instrument.id] || []),
      a,
    ];
    return r;
  }, {});

  Object.values(requestsGroupedByInstId).forEach((value) => {
    value.sort();
  });

  const handleSelectedInstrumentChange = async (e) => {
    setSelectedInstrumentId(e.target.value);
    const params = {
      ...fetchParams,
      numPerPage: defaultNumPerPage,
      pageNumber: 1,
      instrumentID: e.target.value,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(followupRequestActions.fetchFollowupRequests(params));
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Followup Requests</Typography>
            <div>
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
            </div>
          </div>
          <div>
            <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="instrumentSelectLabel"
              value={selectedInstrumentId}
              onChange={handleSelectedInstrumentChange}
              name="followupRequestInstrumentSelect"
              className={classes.select}
            >
              {instrumentList?.map((instrument) => (
                <MenuItem
                  value={instrument.id}
                  key={instrument.id}
                  className={classes.selectItem}
                >
                  {`${telLookUp[instrument.telescope_id].name} / ${
                    instrument.name
                  }`}
                </MenuItem>
              ))}
            </Select>
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

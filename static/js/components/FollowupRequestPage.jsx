import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteIcon from "@mui/icons-material/Delete";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";
import NewDefaultFollowupRequest from "./NewDefaultFollowupRequest";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as defaultFollowupRequestsActions from "../ducks/default_followup_requests";
import * as followupRequestActions from "../ducks/followup_requests";
import * as instrumentActions from "../ducks/instruments";

dayjs.extend(utc);

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
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : null,
  },
  defaultFollowupRequestDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  defaultFollowupRequestDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function followupRequestTitle(
  default_followup_request,
  instrumentList,
  telescopeList
) {
  const { allocation, default_followup_name } = default_followup_request;
  const { instrument_id } = allocation;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${instrument?.name}/${telescope?.nickname} - ${default_followup_name}`;

  return result;
}

export function defaultFollowupRequestInfo(default_followup_request) {
  let result = "";
  if (default_followup_request?.payload) {
    result += `Payload: ${JSON.stringify(
      default_followup_request?.payload,
      null,
      " "
    )}`;
  }
  if (default_followup_request?.source_filter) {
    result += ` / Filter: ${JSON.stringify(
      default_followup_request?.source_filter,
      null,
      " "
    )}`;
  }

  return result;
}

const DefaultFollowupRequestList = ({
  default_followup_requests,
  deletePermission,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultFollowupRequestToDelete, setDefaultFollowupRequestToDelete] =
    useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setDefaultFollowupRequestToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setDefaultFollowupRequestToDelete(null);
  };

  const deleteDefaultFollowupRequest = () => {
    dispatch(
      defaultFollowupRequestsActions.deleteDefaultFollowupRequest(
        defaultFollowupRequestToDelete
      )
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default follow-up request deleted"));
        closeDialog();
      }
    });
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {default_followup_requests?.map((default_followup_request) => (
          <ListItem button key={default_followup_request.id}>
            <ListItemText
              primary={followupRequestTitle(
                default_followup_request,
                instrumentList,
                telescopeList
              )}
              secondary={defaultFollowupRequestInfo(
                default_followup_request,
                groups
              )}
              classes={textClasses}
            />
            <Button
              key={default_followup_request.id}
              id="delete_button"
              classes={{
                root: classes.defaultFollowupRequestDelete,
                disabled: classes.defaultFollowupRequestDeleteDisabled,
              }}
              onClick={() => openDialog(default_followup_request.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteDefaultFollowupRequest}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="default follow-up request"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const defaultNumPerPage = 10;

const FollowupRequestPage = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { followupRequestList, totalMatches } = useSelector(
    (state) => state.followup_requests
  );
  const { defaultFollowupRequestList } = useSelector(
    (state) => state.default_followup_requests
  );
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
    observationStartDate: defaultStartDate,
    observationEndDate: defaultEndDate,
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
    if (action === "changePage" || action === "changeRowsPerPage") {
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

  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
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
            {!followupRequestList ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
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
            )}
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
              {sortedInstrumentList?.map((instrument) => (
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
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">
              List of Default Follow-up Requests
            </Typography>
            <DefaultFollowupRequestList
              default_followup_requests={defaultFollowupRequestList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      <br />
      <br />
      <Grid item md={6} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Filter Followup Requests</Typography>
            <FollowupRequestSelectionForm
              fetchParams={fetchParams}
              setFetchParams={setFetchParams}
            />
          </div>
        </Paper>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Prioritize Followup Requests</Typography>
            <FollowupRequestPrioritizationForm />
          </div>
        </Paper>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">
              Add a New Default Follow-up Request
            </Typography>
            <NewDefaultFollowupRequest />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

DefaultFollowupRequestList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_followup_requests: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default FollowupRequestPage;

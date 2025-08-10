import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import makeStyles from "@mui/styles/makeStyles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";
import ProgressIndicator from "../ProgressIndicators";
import DefaultFollowupRequestList from "./DefaultFollowupRequestList";

import * as followupRequestActions from "../../ducks/followupRequests";
import Spinner from "../Spinner";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  paperContent: {
    padding: "1rem",
  },
}));

const FollowupRequestPage = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments,
  );
  const { followupRequestList, totalMatches } = useSelector(
    (state) => state.followupRequests,
  );
  const { defaultFollowupRequestList } = useSelector(
    (state) => state.default_followup_requests,
  );
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: 10,
    startDate: dayjs().subtract(1, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ"),
    endDate: dayjs().add(1, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ"),
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [tabIndex, setTabIndex] = React.useState(0);

  const handleChangeTab = (event, newValue) => {
    setTabIndex(newValue);
  };

  const handleTableChange = async (action, tableState) => {
    if (action !== "changePage" && action !== "changeRowsPerPage") return;

    const params = {
      ...fetchParams,
      numPerPage: tableState.rowsPerPage,
      pageNumber: tableState.page + 1, // MUI DataGrid is 0-indexed, so we need to add 1 for the API
    };
    await dispatch(followupRequestActions.fetchFollowupRequests(params));
  };

  if (
    !instrumentList.length ||
    !telescopeList.length ||
    !Object.keys(instrumentFormParams).length
  ) {
    return <Spinner />;
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

  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const onDownload = async () => {
    setDownloadProgressTotal(totalMatches);
    const fetchAllRequests = async () => {
      let allFollowupRequests = [];

      for (let i = 1; i <= Math.ceil(totalMatches / 100); i += 1) {
        const params = {
          ...fetchParams,
          pageNumber: i,
          numPerPage: 100,
          noRedux: true,
        };

        // eslint-disable-next-line no-await-in-loop
        const response = await dispatch(
          followupRequestActions.fetchFollowupRequests(params),
        );
        if (response && response.data && response?.status === "success") {
          const { data } = response;
          allFollowupRequests = [
            ...allFollowupRequests,
            ...data.followup_requests,
          ];
          setDownloadProgressCurrent(allFollowupRequests.length);
          setDownloadProgressTotal(data.totalMatches);
        } else if (response && response?.status !== "success") {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (allFollowupRequests?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some follow-up requests. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some follow-up requests, please try again. Follow-up requests fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
      setDownloadProgressCurrent(0);
      setDownloadProgressTotal(0);
      if (
        allFollowupRequests?.length === allFollowupRequests.totalMatches?.length
      ) {
        dispatch(
          showNotification("Follow-up requests downloaded successfully"),
        );
      }
      return allFollowupRequests;
    };

    return await fetchAllRequests();
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Tabs value={tabIndex} onChange={handleChangeTab} centered>
          <Tab label="Follow-up Requests" />
          <Tab label="Default Follow-up Requests" />
        </Tabs>
      </Grid>
      {tabIndex === 0 && (
        <Grid container item xs={12} style={{ paddingTop: 0 }}>
          <Grid item sm={12} md={8}>
            <Paper elevation={1}>
              <div className={classes.paperContent}>
                <Typography variant="h6">List of Followup Requests</Typography>
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
                  fetchParams={fetchParams}
                  onDownload={onDownload}
                />
              </div>
            </Paper>
          </Grid>
          <Grid item sm={12} md={4}>
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
                <Typography variant="h6">
                  Prioritize Followup Requests
                </Typography>
                <FollowupRequestPrioritizationForm />
              </div>
            </Paper>
            <Dialog
              open={downloadProgressTotal > 0}
              style={{ position: "fixed" }}
              maxWidth="md"
            >
              <DialogContent
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <Typography variant="h6" display="inline">
                  Downloading {downloadProgressTotal} follow-up requests
                </Typography>
                <div
                  style={{
                    height: "5rem",
                    width: "5rem",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  <ProgressIndicator
                    current={downloadProgressCurrent}
                    total={downloadProgressTotal}
                    percentage={false}
                  />
                </div>
              </DialogContent>
            </Dialog>
          </Grid>
        </Grid>
      )}
      {tabIndex === 1 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <Paper elevation={1}>
            <DefaultFollowupRequestList
              default_followup_requests={defaultFollowupRequestList}
              deletePermission={permission}
            />
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default FollowupRequestPage;

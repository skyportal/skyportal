import React, { useEffect, useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import FollowupRequestListsBase from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";
import ProgressIndicator from "../ProgressIndicators";
import DefaultFollowupRequestList from "./DefaultFollowupRequestList";

import * as followupRequestActions from "../../ducks/followup_requests";

dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  paperContent: {
    padding: "1rem",
  },
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : undefined,
  },
  defaultFollowupRequestDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  defaultFollowupRequestManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
  defaultFollowupRequestDeleteDisabled: {
    opacity: 0,
  },
}));

const FollowupRequestLists = FollowupRequestListsBase as any;

const defaultNumPerPage = 10;

const FollowupRequestPage = () => {
  const { telescopeList } = useAppSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useAppSelector(
    (state) => state.instruments,
  ) as any;
  const { followupRequestList, totalMatches } = useAppSelector(
    (state) => state.followup_requests,
  ) as any;
  const { defaultFollowupRequestList } = useAppSelector(
    (state) => state.default_followup_requests,
  ) as any;
  const currentUser = useAppSelector((state) => state.profile);
  const { classes } = useStyles() as any;
  const dispatch = useAppDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  const defaultStartDate = dayjs()
    .subtract(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
    startDate: defaultStartDate,
    endDate: defaultEndDate,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [tabIndex, setTabIndex] = React.useState(0);

  useEffect(() => {
    // everytime the list of followup requests is updated, we set the fetchParams in redux
    dispatch({
      type: followupRequestActions.UPDATE_FOLLOWUP_FETCH_PARAMS,
      data: fetchParams,
    });
  }, [dispatch, fetchParams]);

  const handleChangeTab = (event: any, newValue: number) => {
    setTabIndex(newValue);
  };

  const handlePageChange = async (page: number, numPerPage: number) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(followupRequestActions.fetchFollowupRequests(params));
  };

  const handleTableChange = async (action: string, tableState: any) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      return handlePageChange(tableState.page, tableState.rowsPerPage);
    }
    return null;
  };

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>Loading information...</p>;
  }

  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1: any, i2: any) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const onDownload = async () => {
    setDownloadProgressTotal(totalMatches);
    const fetchAllRequests = async (currentFetchParams: any) => {
      let allFollowupRequests: any[] = [];

      for (let i = 1; i <= Math.ceil(totalMatches / 100); i += 1) {
        const params = {
          ...currentFetchParams,
          pageNumber: i,
          numPerPage: 100,
          noRedux: true,
        };

        const response: any = await dispatch(
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
        allFollowupRequests?.length ===
        (allFollowupRequests as any).totalMatches?.length
      ) {
        dispatch(
          showNotification("Follow-up requests downloaded successfully"),
        );
      }
      return allFollowupRequests;
    };

    const allFollowupRequests = await fetchAllRequests(fetchParams);

    return allFollowupRequests;
  };

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Tabs value={tabIndex} onChange={handleChangeTab} centered>
          <Tab label="Follow-up Requests" />
          <Tab label="Default Follow-up Requests" />
        </Tabs>
      </Grid>
      {tabIndex === 0 && (
        <Grid container size={12} style={{ paddingTop: 0 }}>
          <Grid size={{ sm: 12, md: 8 }}>
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
                      handleTableChange={handleTableChange as any}
                      totalMatches={totalMatches}
                      serverSide
                      showObject
                      fetchParams={fetchParams}
                      onDownload={onDownload as any}
                    />
                  </div>
                )}
              </div>
            </Paper>
          </Grid>
          <Grid size={{ sm: 12, md: 4 }}>
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
            <Dialog open={downloadProgressTotal > 0} maxWidth="md">
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
        <Grid size={12} style={{ paddingTop: 0 }}>
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

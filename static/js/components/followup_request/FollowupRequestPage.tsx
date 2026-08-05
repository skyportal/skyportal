import { useGetProfileQuery } from "../../ducks/profile";
import React, { useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
} from "../../ducks/instruments";
import { useGetDefaultFollowupRequestsQuery } from "../../ducks/default_followup_requests";
import FollowupRequestListsBase from "./FollowupRequestLists";
import FollowupHealth from "./FollowupHealth";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";
import ProgressIndicator from "../ProgressIndicators";
import DefaultFollowupRequestList from "./DefaultFollowupRequestList";
import Paper from "../Paper";

import {
  useGetFollowupRequestsQuery,
  useLazyGetFollowupRequestsQuery,
} from "../../ducks/followup_requests";

dayjs.extend(utc);

const FollowupRequestLists = FollowupRequestListsBase as any;

const defaultNumPerPage = 10;

const FollowupRequestPage = () => {
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const { data: defaultFollowupRequestList } =
    useGetDefaultFollowupRequestsQuery();
  const { data: currentUser } = useGetProfileQuery();
  const dispatch = useAppDispatch();

  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage allocations") ||
    false;

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

  const { data: followupRequestsData } =
    useGetFollowupRequestsQuery(fetchParams);
  const followupRequestList = followupRequestsData?.followup_requests;
  const totalMatches = followupRequestsData?.totalMatches ?? 0;
  const [triggerFetchFollowupRequests] = useLazyGetFollowupRequestsQuery();

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [tabIndex, setTabIndex] = React.useState(0);

  const handleChangeTab = (_event: any, newValue: number) => {
    setTabIndex(newValue);
  };

  const handlePageChange = async (page: number, numPerPage: number) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Updating fetchParams re-keys the followup-requests query, which refetches.
    setFetchParams(params);
  };

  const handleTableChange = async (action: string, tableState: any) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      return handlePageChange(tableState.page, tableState.rowsPerPage);
    }
    return null;
  };

  if (
    !instrumentList.length ||
    !telescopeList.length ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return "Loading information...";
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
        };

        try {
          const data: any = await triggerFetchFollowupRequests(params).unwrap();
          allFollowupRequests = [
            ...allFollowupRequests,
            ...data.followup_requests,
          ];
          setDownloadProgressCurrent(allFollowupRequests.length);
          setDownloadProgressTotal(data.totalMatches);
        } catch {
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

    return await fetchAllRequests(fetchParams);
  };

  return (
    <div>
      <Tabs value={tabIndex} onChange={handleChangeTab} centered>
        <Tab label="Follow-up Requests" />
        <Tab label="Default Follow-up Requests" />
      </Tabs>
      {tabIndex === 0 && (
        <Grid
          container
          size={12}
          sx={{ paddingTop: 0, borderTop: 1, borderColor: "divider" }}
        >
          <Grid size={12}>
            <FollowupHealth />
          </Grid>
          <Grid size={{ sm: 12, md: 8 }}>
            <Paper>
              <Typography variant="h6">List of Followup Requests</Typography>
              {!followupRequestList ? (
                <CircularProgress />
              ) : (
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
              )}
            </Paper>
          </Grid>
          <Grid size={{ sm: 12, md: 4 }}>
            <Paper
              sx={{ marginBottom: 2 }}
              data-testid="filter-followup-requests-form"
            >
              <Typography variant="h6">Filter Followup Requests</Typography>
              <FollowupRequestSelectionForm
                fetchParams={fetchParams}
                setFetchParams={setFetchParams}
              />
            </Paper>
            <Paper>
              <Typography variant="h6">Prioritize Followup Requests</Typography>
              <FollowupRequestPrioritizationForm fetchParams={fetchParams} />
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
                <Typography
                  variant="h6"
                  sx={{
                    display: "inline",
                  }}
                >
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
        <DefaultFollowupRequestList
          default_followup_requests={defaultFollowupRequestList || []}
          deletePermission={permission}
        />
      )}
    </div>
  );
};

export default FollowupRequestPage;

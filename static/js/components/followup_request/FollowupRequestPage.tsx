import { useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetInstrumentsQuery,
  useGetInstrumentFormsQuery,
} from "../../ducks/instruments";
import { useGetDefaultFollowupRequestsQuery } from "../../ducks/default_followup_requests";
import {
  useGetFollowupRequestsQuery,
  useLazyGetFollowupRequestsQuery,
} from "../../ducks/followup_requests";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupHealth, { WINDOWS } from "./FollowupHealth";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";
import DefaultFollowupRequestList from "./DefaultFollowupRequestList";
import { DownloadProgressDialog } from "../ProgressIndicators";
import Paper from "../Paper";
import Spinner from "../Spinner";

const DOWNLOAD_PAGE_SIZE = 100;

const FollowupRequestPage = () => {
  const dispatch = useAppDispatch();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const { data: defaultFollowupRequestList = [] } =
    useGetDefaultFollowupRequestsQuery();
  const { data: currentUser } = useGetProfileQuery();
  const [tabIndex, setTabIndex] = useState(0);
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);
  const [fetchParams, setFetchParams] = useState<Record<string, any>>({
    pageNumber: 1,
    numPerPage: 25,
    sortBy: "created_at",
    sortOrder: "desc",
  });
  const [now] = useState(() => Date.now());
  const [windowKey, setWindowKey] = useState("1w");
  const { ms } = WINDOWS.find((w) => w.key === windowKey)!;
  const windowStartDate =
    ms === Infinity ? undefined : new Date(now - ms).toISOString();
  const listParams = {
    ...fetchParams,
    startDate: fetchParams["startDate"] ?? windowStartDate,
  };
  const { data: followupRequestsData } =
    useGetFollowupRequestsQuery(listParams);
  const [triggerFetchFollowupRequests] = useLazyGetFollowupRequestsQuery();
  const totalMatches = followupRequestsData?.totalMatches ?? 0;

  if (
    !instrumentList.length ||
    !telescopeList.length ||
    !Object.keys(instrumentFormParams).length
  ) {
    return <Spinner />;
  }

  const onDownload = async () => {
    let allFollowupRequests: any[] = [];
    setDownloadProgressTotal(totalMatches);
    for (
      let page = 1;
      page <= Math.ceil(totalMatches / DOWNLOAD_PAGE_SIZE);
      page += 1
    ) {
      const { data, error }: any = await triggerFetchFollowupRequests({
        ...listParams,
        pageNumber: page,
        numPerPage: DOWNLOAD_PAGE_SIZE,
      });
      if (error) {
        dispatch(
          showNotification(
            allFollowupRequests.length
              ? "Failed to fetch some follow-up requests, please try again. Follow-up requests fetched so far will be downloaded."
              : "Failed to fetch some follow-up requests. Download cancelled.",
            "error",
          ),
        );
        break;
      }
      allFollowupRequests = [...allFollowupRequests, ...data.followup_requests];
      setDownloadProgressCurrent(allFollowupRequests.length);
      setDownloadProgressTotal(data.totalMatches);
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    return allFollowupRequests;
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Tabs
        value={tabIndex}
        onChange={(_e, value) => setTabIndex(value)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Follow-up Requests" />
        <Tab label="Default Follow-up Requests" />
      </Tabs>
      {tabIndex === 0 && (
        <Grid container spacing={2}>
          <Grid size={12}>
            <FollowupHealth
              windowKey={windowKey}
              onWindowChange={(key) => {
                setWindowKey(key);
                setFetchParams({ ...fetchParams, pageNumber: 1 });
              }}
              startDate={windowStartDate}
            />
          </Grid>
          <Grid size={{ sm: 12, md: 8 }}>
            <Paper>
              <Typography variant="h6">List of Followup Requests</Typography>
              {followupRequestsData ? (
                <FollowupRequestLists
                  followupRequests={followupRequestsData.followup_requests}
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  pageNumber={fetchParams["pageNumber"]}
                  numPerPage={fetchParams["numPerPage"]}
                  onPaginationChange={(page, numPerPage) =>
                    setFetchParams({
                      ...fetchParams,
                      pageNumber: page + 1,
                      numPerPage,
                    })
                  }
                  totalMatches={totalMatches}
                  serverSide
                  showObject
                  onDownload={onDownload}
                />
              ) : (
                <CircularProgress />
              )}
            </Paper>
          </Grid>
          <Grid
            size={{ sm: 12, md: 4 }}
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            <Paper data-testid="filter-followup-requests-form">
              <Typography variant="h6">Filter Followup Requests</Typography>
              <FollowupRequestSelectionForm
                fetchParams={listParams}
                setFetchParams={setFetchParams}
              />
            </Paper>
            <Paper>
              <Typography variant="h6">Prioritize Followup Requests</Typography>
              <FollowupRequestPrioritizationForm fetchParams={listParams} />
            </Paper>
          </Grid>
        </Grid>
      )}
      {tabIndex === 1 && (
        <DefaultFollowupRequestList
          default_followup_requests={defaultFollowupRequestList}
          deletePermission={
            currentUser?.permissions?.includes("System admin") ||
            currentUser?.permissions?.includes("Manage allocations") ||
            false
          }
        />
      )}
      <DownloadProgressDialog
        current={downloadProgressCurrent}
        total={downloadProgressTotal}
        label="follow-up requests"
      />
    </Box>
  );
};

export default FollowupRequestPage;

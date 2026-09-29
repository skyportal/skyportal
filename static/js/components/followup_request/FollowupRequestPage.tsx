import { useState } from "react";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import useDebounced from "../../hooks/useDebounced";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetDefaultFollowupRequestsQuery } from "../../ducks/default_followup_requests";
import {
  useGetFollowupRequestsQuery,
  useLazyGetFollowupRequestsQuery,
} from "../../ducks/followup_requests";
import { DownloadProgressDialog } from "../ProgressIndicators";
import DefaultFollowupRequestList from "./DefaultFollowupRequestList";
import FollowupRequestFilters, {
  FollowupRequestFiltersState,
  WINDOWS,
} from "./FollowupRequestFilters";
import FollowupRequestTable from "./FollowupRequestTable";

const DOWNLOAD_PAGE_SIZE = 100;

const FollowupRequestPage = () => {
  const dispatch = useAppDispatch();
  const { data: defaultFollowupRequestList = [] } =
    useGetDefaultFollowupRequestsQuery();
  const { data: currentUser } = useGetProfileQuery();
  const [tabIndex, setTabIndex] = useState(0);
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);
  const [now] = useState(() => Date.now());
  const [filters, setFilters] = useState<FollowupRequestFiltersState>({
    windowKey: "1w",
  });
  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 25,
  });
  const [sortModel, setSortModel] = useState<any[]>([
    { field: "created_at", sort: "desc" },
  ]);
  const sourceID = useDebounced(filters.sourceID, 400);
  const priorityThreshold = useDebounced(filters.priorityThreshold, 400);

  const { windowKey, startDate, endDate, status, ...otherFilters } = filters;
  const { ms } = WINDOWS.find(({ key }) => key === windowKey)!;
  const countParams = {
    ...otherFilters,
    sourceID,
    priorityThreshold,
    ...(windowKey === "custom"
      ? { startDate, endDate }
      : ms !== Infinity && { startDate: new Date(now - ms).toISOString() }),
  };
  const listParams = {
    ...countParams,
    status,
    pageNumber: paginationModel.page + 1,
    numPerPage: paginationModel.pageSize,
    sortBy: sortModel[0]?.field ?? "created_at",
    sortOrder: sortModel[0]?.sort ?? "desc",
  };
  const { data, isFetching } = useGetFollowupRequestsQuery(listParams);
  const [triggerFetchFollowupRequests] = useLazyGetFollowupRequestsQuery();
  const totalMatches = data?.totalMatches ?? 0;

  const resetPage = () => setPaginationModel({ ...paginationModel, page: 0 });

  const onDownload = async () => {
    let allFollowupRequests: any[] = [];
    setDownloadProgressTotal(totalMatches);
    for (
      let page = 1;
      page <= Math.ceil(totalMatches / DOWNLOAD_PAGE_SIZE);
      page += 1
    ) {
      const { data: pageData, error }: any = await triggerFetchFollowupRequests(
        {
          ...listParams,
          pageNumber: page,
          numPerPage: DOWNLOAD_PAGE_SIZE,
        },
      );
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
      allFollowupRequests = [
        ...allFollowupRequests,
        ...pageData.followup_requests,
      ];
      setDownloadProgressCurrent(allFollowupRequests.length);
      setDownloadProgressTotal(pageData.totalMatches);
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
        <>
          <FollowupRequestFilters
            filters={filters}
            onChange={(changes) => {
              setFilters({ ...filters, ...changes });
              resetPage();
            }}
            countParams={countParams}
          />
          <FollowupRequestTable
            requests={data?.followup_requests ?? []}
            totalMatches={totalMatches}
            loading={isFetching}
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            sortModel={sortModel}
            onSortModelChange={(model) => {
              setSortModel(model);
              resetPage();
            }}
            onDownload={onDownload}
          />
        </>
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

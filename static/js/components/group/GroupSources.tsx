import { useGetGroupsQuery } from "../../ducks/groups";
import { useState } from "react";
import { useAppDispatch } from "../../types/hooks";

import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import { showNotification } from "baselayer/components/Notifications";

import Paper from "../Paper";
import SourceTable from "../source/SourceTable";
import withRouter from "../withRouter";
import ProgressIndicator from "../ProgressIndicators";
import Spinner from "../Spinner";

import {
  useFetchSavedGroupSourcesQuery,
  useFetchPendingGroupSourcesQuery,
  useLazyFetchSavedGroupSourcesQuery,
} from "../../ducks/sources";

interface GroupSourcesProps {
  route: {
    id: string;
  };
}

const GroupSources = ({ route }: GroupSourcesProps) => {
  const dispatch = useAppDispatch();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [savedSourcesRowsPerPage, setSavedSourcesRowsPerPage] = useState(10);
  const [pendingSourcesRowsPerPage, setPendingSourcesRowsPerPage] =
    useState(10);
  const [sorting, setSorting] = useState<any>(null);
  const [filtering, setFiltering] = useState<any>(null);
  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [savedQueryParams, setSavedQueryParams] = useState<any>({
    group_ids: [route.id],
    pageNumber: 1,
    numPerPage: 10,
  });
  const [pendingQueryParams, setPendingQueryParams] = useState<any>({
    group_ids: [route.id],
    pageNumber: 1,
    numPerPage: 10,
  });

  const { data: savedSourcesState } =
    useFetchSavedGroupSourcesQuery(savedQueryParams);
  const { data: pendingSourcesState } =
    useFetchPendingGroupSourcesQuery(pendingQueryParams);
  const [fetchSavedGroupSourcesTrigger] = useLazyFetchSavedGroupSourcesQuery();

  if (
    !savedSourcesState?.sources ||
    !pendingSourcesState?.sources ||
    savedSourcesState["group_id"] !== parseInt(route.id, 10) ||
    pendingSourcesState["group_id"] !== parseInt(route.id, 10)
  )
    return <Spinner />;

  const groupID = parseInt(route.id, 10);

  const groupName = groups?.filter((g: any) => g.id === groupID)[0]?.name || "";

  const handleSavedSourcesTableSorting = (sortData: any, filterData: any) => {
    setSavedQueryParams({
      ...filterData,
      group_ids: [route.id],
      pageNumber: 1,
      numPerPage: savedSourcesRowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    });
  };

  const handleSavedSourcesTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setSavedSourcesRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      group_ids: [route.id],
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    setSavedQueryParams(data);
    setSorting(sortData);
    setFiltering(filterData);
  };

  const handlePendingSourcesTableSorting = (sortData: any, filterData: any) => {
    setPendingQueryParams({
      ...filterData,
      group_ids: [route.id],
      pageNumber: 1,
      numPerPage: pendingSourcesRowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    });
    setSorting(sortData);
    setFiltering(filterData);
  };

  const handlePendingSourcesTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setPendingSourcesRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      group_ids: [route.id],
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    setPendingQueryParams(data);
  };

  const handleSourcesDownload = async () => {
    const sourceAll: any[] = [];
    if (savedSourcesState.totalMatches === 0) {
      await dispatch(showNotification("No sources to download", "warning"));
    } else {
      setDownloadProgressTotal(savedSourcesState.totalMatches);
      for (
        let i = 1;
        i <=
        Math.ceil(
          savedSourcesState.totalMatches / savedSourcesState.numPerPage,
        );
        i += 1
      ) {
        const data: any = {
          ...filtering,
          group_ids: [route.id],
          pageNumber: i,
          numPerPage: savedSourcesState.numPerPage,
        };
        if (sorting) {
          data.sortBy = sorting.name;
          data.sortOrder = sorting.direction;
        }
        /* eslint-disable no-await-in-loop */
        try {
          const result: any =
            await fetchSavedGroupSourcesTrigger(data).unwrap();
          sourceAll.push(...result.sources);
          setDownloadProgressCurrent(sourceAll.length);
          setDownloadProgressTotal(savedSourcesState.totalMatches);
        } catch {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (sourceAll?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some sources. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some sources, please try again. Sources fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (sourceAll?.length === savedSourcesState.totalMatches) {
      dispatch(showNotification("Sources downloaded successfully"));
    }
    return sourceAll;
  };

  return (
    <Paper
      sx={{ display: "flex", flexDirection: "column", gap: "1rem", mt: 2 }}
    >
      {!!savedSourcesState.sources && (
        <SourceTable
          sources={savedSourcesState.sources}
          title={`${groupName} sources`}
          sourceStatus="saved"
          groupID={groupID}
          paginateCallback={handleSavedSourcesTablePagination}
          pageNumber={savedSourcesState.pageNumber}
          totalMatches={savedSourcesState.totalMatches}
          numPerPage={savedSourcesState.numPerPage}
          sortingCallback={handleSavedSourcesTableSorting}
          downloadCallback={handleSourcesDownload}
        />
      )}
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
          downloadCallback={handleSourcesDownload}
        />
      )}
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
            Downloading {downloadProgressTotal} sources
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
    </Paper>
  );
};

export default withRouter(GroupSources);

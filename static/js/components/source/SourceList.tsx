import { useState } from "react";

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import SourceTable from "./SourceTable";
import ProgressIndicator from "../ProgressIndicators";
import { useAppDispatch } from "../../types/hooks";
import {
  useFetchSourcesQuery,
  useLazyFetchSourcesQuery,
} from "../../ducks/sources";
import { useGetDbInfoQuery } from "../../ducks/dbInfo";

const EMPTY_SOURCES: any[] = [];

const SourceList = () => {
  const dispatch = useAppDispatch();

  const [queryParams, setQueryParams] = useState<any>({});
  const { data: sourcesState, isFetching } = useFetchSourcesQuery(queryParams);
  const [fetchSourcesTrigger] = useLazyFetchSourcesQuery();
  const sourceTableEmpty = !!useGetDbInfoQuery().data?.["source_table_empty"];

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const handleSourceTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
      queryID: pageNumber > 1 ? (sourcesState?.queryID ?? null) : null,
    };
    if (sortData?.name) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    setQueryParams(data);
    fetchSourcesTrigger(data)
      .unwrap()
      .catch(() => {
        if (!data.queryID) return;
        const retry = { ...data, queryID: null };
        setQueryParams(retry);
        fetchSourcesTrigger(retry);
      });
  };

  const handleSourceTableSorting = (sortData: any, filterData: any) =>
    handleSourceTablePagination(
      1,
      queryParams.numPerPage,
      sortData,
      filterData,
    );

  const handleSourcesDownload = async () => {
    if (!sourcesState?.totalMatches) {
      dispatch(showNotification("No sources to download", "warning"));
      return [];
    }
    const { totalMatches, numPerPage } = sourcesState;
    const sourceAll: any[] = [];
    let downloadQueryID: string | null = null;

    setDownloadProgressTotal(totalMatches);
    for (let i = 1; i <= Math.ceil(totalMatches / numPerPage); i += 1) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const result: any = await fetchSourcesTrigger({
          ...queryParams,
          pageNumber: i,
          numPerPage,
          queryID: i > 1 ? downloadQueryID : null,
        }).unwrap();
        downloadQueryID = result?.queryID ?? downloadQueryID;
        sourceAll.push(...result.sources);
        setDownloadProgressCurrent(sourceAll.length);
      } catch {
        dispatch(
          showNotification(
            sourceAll.length
              ? "Failed to fetch some sources, please try again. Sources fetched so far will be downloaded."
              : "Failed to fetch some sources. Download cancelled.",
            "error",
          ),
        );
        break;
      }
    }
    setDownloadProgressCurrent(0);
    setDownloadProgressTotal(0);
    if (sourceAll.length === totalMatches) {
      dispatch(showNotification("Sources downloaded successfully"));
    }
    return sourceAll;
  };

  return (
    <>
      {sourceTableEmpty && (
        <Alert severity="warning">
          <AlertTitle>The Sources table is currently empty</AlertTitle>
          For help with initializing the database, see the{" "}
          <a href="https://skyportal.io/docs/setup.html">
            getting started documentation
          </a>
          . Or click the <b>+</b> icon in the upper right corner of the table to
          add a source.
        </Alert>
      )}
      <SourceTable
        sources={sourcesState?.sources || EMPTY_SOURCES}
        paginateCallback={handleSourceTablePagination}
        totalMatches={sourcesState?.totalMatches || 0}
        pageNumber={sourcesState?.pageNumber || 1}
        numPerPage={sourcesState?.numPerPage || 30}
        sortingCallback={handleSourceTableSorting}
        downloadCallback={handleSourcesDownload}
        fixedHeader
        isLoading={isFetching}
      />
      <Dialog open={downloadProgressTotal > 0} maxWidth="md">
        <DialogContent
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <Typography variant="h6">
            Downloading {downloadProgressTotal} sources
          </Typography>
          <Box sx={{ height: "5rem", width: "5rem" }}>
            <ProgressIndicator
              current={downloadProgressCurrent}
              total={downloadProgressTotal}
              percentage={false}
            />
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceList;

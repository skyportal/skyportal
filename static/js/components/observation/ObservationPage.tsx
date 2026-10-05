import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { showNotification } from "baselayer/components/Notifications";
import { filterOutEmptyValues } from "../../API";
import ExecutedObservationsTable from "./ExecutedObservationsTable";
import QueuedObservationsTable from "./QueuedObservationsTable";
import QueueAPIDisplay from "./QueueAPIDisplay";
import { DownloadProgressDialog } from "../ProgressIndicators";
import Paper from "../Paper";
import Spinner from "../Spinner";
import SkymapTriggerAPIDisplay from "./SkymapTriggerAPIDisplay";

import {
  useGetObservationsQuery,
  useLazyGetObservationsQuery,
} from "../../ducks/observations";
import {
  useGetQueuedObservationsQuery,
  useLazyGetQueuedObservationsQuery,
} from "../../ducks/queued_observations";
import { useAppDispatch } from "../../types/hooks";

const defaultNumPerPage = 25;

const ObservationPage = () => {
  const { data: currentUser } = useGetProfileQuery();
  const dispatch = useAppDispatch();

  const [fetchExecutedParams, setFetchExecutedParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const [fetchQueuedParams, setFetchQueuedParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const { data: observations } = useGetObservationsQuery(fetchExecutedParams);
  const [fetchObservations] = useLazyGetObservationsQuery();

  const { data: queuedObservations } =
    useGetQueuedObservationsQuery(fetchQueuedParams);
  const [fetchQueuedObservations] = useLazyGetQueuedObservationsQuery();

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  const [tabIndex, setTabIndex] = useState(0);
  const [filterModel, setFilterModel] = useState({
    items: [],
    quickFilterValues: [],
  });

  if (observations == null || queuedObservations == null) {
    return <Spinner context="observations" />;
  }

  const handleExecutedPageChange = async (
    page: number,
    numPerPage: number,
    sortData?: any,
  ) => {
    const params = {
      ...fetchExecutedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      params.sortBy = sortData.name;
      params.sortOrder = sortData.direction;
    }
    setFetchExecutedParams(params);
  };

  const handleQueuedPageChange = async (
    page: number,
    numPerPage: number,
    _sortData?: any,
  ) => {
    const params = {
      ...fetchQueuedParams,
      numPerPage,
      pageNumber: page + 1,
    };
    setFetchQueuedParams(params);
  };

  const handleExecutedTableSorting = async (sortData: any) => {
    const params = {
      ...fetchExecutedParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchExecutedParams(params);
  };

  const handleQueuedTableSorting = async (sortData: any) => {
    const params = {
      ...fetchQueuedParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchQueuedParams(params);
  };

  const handleExecutedTableChange = (action: string, tableState: any) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handleExecutedPageChange(
        tableState.page + 1,
        tableState.rowsPerPage,
        tableState.sortOrder,
      );
    }
    if (action === "sort") {
      if (tableState.sortOrder.direction === "none") {
        handleExecutedPageChange(1, tableState.rowsPerPage, {});
      } else {
        handleExecutedTableSorting(tableState.sortOrder);
      }
    }
  };

  const handleQueuedTableChange = (action: string, tableState: any) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handleQueuedPageChange(tableState.page, tableState.rowsPerPage);
    }
    if (action === "sort") {
      if (tableState.sortOrder.direction === "none") {
        handleQueuedPageChange(1, tableState.rowsPerPage, {});
      } else {
        handleQueuedTableSorting(tableState.sortOrder);
      }
    }
  };

  const handleExecutedTableFilter = async (
    pageNumber: number,
    numPerPage: number,
    filterData?: any,
  ) => {
    const params = {
      ...fetchExecutedParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.instrumentName = filterData.instrumentName;
    }
    setFetchExecutedParams(params);
  };

  const handleQueuedTableFilter = async (
    pageNumber: number,
    numPerPage: number,
    filterData?: any,
  ) => {
    const params = {
      ...fetchQueuedParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.instrumentName = filterData.instrumentName;
    }
    setFetchQueuedParams(params);
  };

  const handleExecutedFilterSubmit = async (formData: any) => {
    const data = filterOutEmptyValues(formData);
    handleExecutedTableFilter(1, defaultNumPerPage, data);
  };

  const handleQueuedFilterSubmit = async (formData: any) => {
    const data = filterOutEmptyValues(formData);
    handleQueuedTableFilter(1, defaultNumPerPage, data);
  };

  const handleExecutedDownload = async () => {
    const observationsAll: any[] = [];
    const totalMatches = observations.totalMatches ?? 0;
    if (totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(totalMatches);
      for (
        let i = 1;
        i <= Math.ceil(totalMatches / fetchExecutedParams.numPerPage);
        i += 1
      ) {
        const data = {
          ...fetchExecutedParams,
          pageNumber: i,
        };

        try {
          const result: any = await fetchObservations(data).unwrap();
          observationsAll.push(...result.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(totalMatches);
        } catch {
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (observations.observations?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some observations. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some observations, please try again. Observations fetched so far will be downloaded.",
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
    if (observationsAll?.length === observations.totalMatches) {
      dispatch(showNotification("Observations downloaded successfully"));
    }
    return observationsAll;
  };

  const handleQueuedDownload = async () => {
    const observationsAll: any[] = [];

    if (queuedObservations.totalMatches === 0) {
      dispatch(showNotification("No observations to download", "warning"));
    } else {
      setDownloadProgressTotal(queuedObservations.totalMatches);
      for (
        let i = 1;
        i <=
        Math.ceil(
          queuedObservations.totalMatches / fetchQueuedParams.numPerPage,
        );
        i += 1
      ) {
        const data = {
          ...fetchQueuedParams,
          pageNumber: i,
        };

        try {
          const result: any = await fetchQueuedObservations(data).unwrap();
          observationsAll.push(...result.observations);
          setDownloadProgressCurrent(observationsAll.length);
          setDownloadProgressTotal(queuedObservations.totalMatches);
        } catch {
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (queuedObservations.observations?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some observations. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some observations, please try again. Observations fetched so far will be downloaded.",
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
    if (observationsAll?.length === queuedObservations.totalMatches) {
      dispatch(showNotification("Observations downloaded successfully"));
    }
    return observationsAll;
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Tabs
        value={tabIndex}
        onChange={(_event, value) => setTabIndex(value)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Executed Observations" />
        <Tab label="Queued Observations" />
        {currentUser?.permissions?.includes("System admin") && (
          <Tab label="Queue Interactions" />
        )}
      </Tabs>
      {tabIndex === 0 && (
        <>
          <ExecutedObservationsTable
            observations={observations.observations ?? []}
            pageNumber={fetchExecutedParams.pageNumber}
            numPerPage={fetchExecutedParams.numPerPage}
            handleTableChange={handleExecutedTableChange}
            handleFilterSubmit={handleExecutedFilterSubmit}
            totalMatches={observations.totalMatches ?? 0}
            downloadCallback={handleExecutedDownload}
            filterModel={filterModel}
            onFilterModelChange={setFilterModel}
            fixedHeader
          />
          <DownloadProgressDialog
            current={downloadProgressCurrent}
            total={downloadProgressTotal}
            label="observations"
          />
        </>
      )}
      {tabIndex === 1 && (
        <QueuedObservationsTable
          observations={queuedObservations.observations ?? []}
          pageNumber={fetchQueuedParams.pageNumber}
          numPerPage={fetchQueuedParams.numPerPage}
          handleTableChange={handleQueuedTableChange}
          handleFilterSubmit={handleQueuedFilterSubmit}
          totalMatches={queuedObservations.totalMatches ?? 0}
          downloadCallback={handleQueuedDownload}
          filterModel={filterModel}
          onFilterModelChange={setFilterModel}
          fixedHeader
        />
      )}
      {tabIndex === 2 && currentUser?.permissions?.includes("System admin") && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper>
              <Typography variant="h6">Queue Interaction</Typography>
              <QueueAPIDisplay />
            </Paper>
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <Paper>
              <Typography variant="h6">Skymap Queue Interaction</Typography>
              <SkymapTriggerAPIDisplay />
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default ObservationPage;

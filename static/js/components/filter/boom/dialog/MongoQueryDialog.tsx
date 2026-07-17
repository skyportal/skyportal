import { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  IconButton,
  Snackbar,
  Alert,
  CircularProgress,
  Divider,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
  Link,
} from "@mui/material";
import {
  Close as CloseIcon,
  PlayArrow as RunIcon,
  Fullscreen as FullscreenIcon,
  FirstPage as FirstPageIcon,
  LastPage as LastPageIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Download as DownloadIcon,
} from "@mui/icons-material";
import { Controller, useForm } from "react-hook-form";
import { useCurrentBuilder } from "../../../../hooks/useContexts";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import FormValidationError from "../../../FormValidationError";
import ReactJson from "react-json-view";
import { makeStyles } from "tss-react/mui";
import { useAppDispatch } from "../../../../types/hooks";
import { useBoomFilterVersion } from "../../../../ducks/boom_filter";
import { useRunBoomFilterMutation } from "../../../../ducks/boom_run_filter";
import { useGetProfileQuery } from "../../../../ducks/profile";
import PipelineViewer from "./PipelineViewer";
import FullscreenResultsDialog from "./FullscreenResultsDialog";

const useStyles = makeStyles()((_theme) => ({
  timeRange: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.5rem",
    marginBottom: "1rem",
  },
}));

// Helper function to properly combine user pipeline with additional stages
// Note: Sorting is now handled by the API, not in the pipeline
const combineWithPipeline = (
  userPipeline: any[],
  additionalStages: any[] = [],
  _isCountOnly = false,
) => {
  const finalPipeline: any[] = [];

  // Add user pipeline stages
  finalPipeline.push(...userPipeline);

  // Add any additional stages (like $limit, $size) before the final project stage
  if (additionalStages && additionalStages.length > 0) {
    finalPipeline.unshift(...additionalStages);
  }

  return finalPipeline;
};

const resetPaginationAndQueryState = (setters: any) => {
  const {
    setExpandedCells,
    setCurrentPage,
    setTotalDocuments,
    setIsLoadingPage,
    setPageCursors,
    setLastDocumentId,
    setHasNextPage,
    setLastPageOffset,
    setDisplayResults,
    setQueryCompleted,
  } = setters;

  setExpandedCells(new Set());
  setCurrentPage(1);
  setTotalDocuments(0);
  setIsLoadingPage(false);
  setPageCursors(new Map());
  setLastDocumentId(null);
  setHasNextPage(false);
  setLastPageOffset(0);
  setDisplayResults({ data: [] });

  // Optional setters that may not be available in all contexts
  if (setQueryCompleted) setQueryCompleted(false);
};

const getConvertedDatesFromForm = (getValues: any) => {
  const formData = getValues();
  let startDate: any, endDate: any;

  function utcToJulianDate(date: any) {
    const d = new Date(date);
    const time = d.getTime();
    const daysSinceEpoch = time / 86400000;
    const JD_UNIX_EPOCH = 2440587.5;
    return JD_UNIX_EPOCH + daysSinceEpoch;
  }

  if (formData.startDate) {
    startDate = utcToJulianDate(formData.startDate);
  }
  if (formData.endDate) {
    endDate = utcToJulianDate(formData.endDate);
  }

  return { startDate, endDate };
};

const MongoQueryDialog = () => {
  const {
    mongoDialog = { open: false },
    setMongoDialog,
    generateMongoQuery,
    getFormattedMongoQuery,
    hasValidQuery,
  } = useCurrentBuilder();
  const { classes } = useStyles();

  const { data: boomFilterVersion } = useBoomFilterVersion();
  const filter_stream = boomFilterVersion?.stream?.name?.split(" ")[0];
  const filter_id = boomFilterVersion?.id;
  const dispatch = useAppDispatch();
  const [runBoomFilter, { reset: clearBoomFilter }] =
    useRunBoomFilterMutation();
  const { data: profile } = useGetProfileQuery();
  const { useAMPM } = profile?.preferences ?? {};

  const [copySuccess, setCopySuccess] = useState(false);
  const [displayResults, setDisplayResults] = useState<{ data?: any[] }>({
    data: [],
  }); // Local results for display
  const [selectedCollection, setSelectedCollection] = useState(
    filter_stream === "ZTF"
      ? "ZTF_alerts"
      : filter_stream === "LSST"
        ? "LSST_alerts"
        : "",
  );
  const [isRunning, setIsRunning] = useState(false);
  const [queryError, setQueryError] = useState<any>(null);
  const [dateValidationError, setDateValidationError] = useState<any>(null);
  const [showPipeline, setShowPipeline] = useState(true);
  const [pipelineView, setPipelineView] = useState("complete");
  const [connectionStatus, setConnectionStatus] = useState("unknown");
  const [expandedCells, setExpandedCells] = useState<Set<any>>(new Set());
  const [expandedStages, setExpandedStages] = useState<Set<any>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [pageSize] = useState(50);
  const [isLoadingPage, setIsLoadingPage] = useState(false);
  const [pageCursors, setPageCursors] = useState<Map<any, any>>(new Map());
  const [pageDataCache, setPageDataCache] = useState<Map<any, any>>(new Map()); // Cache actual page data
  const [, setLastDocumentId] = useState<any>(null);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [queryCompleted, setQueryCompleted] = useState(false);
  const [lastQueryString, setLastQueryString] = useState("");
  const [, setLastPageOffset] = useState(0);

  useEffect(() => {
    if (hasValidQuery()) {
      const currentQueryString = getFormattedMongoQuery();

      if (lastQueryString && lastQueryString !== currentQueryString) {
        clearBoomFilter();
        resetPaginationAndQueryState({
          setExpandedCells,
          setCurrentPage,
          setTotalDocuments,
          setIsLoadingPage,
          setPageCursors,
          setLastDocumentId,
          setHasNextPage,
          setLastPageOffset,
          setDisplayResults,
          setQueryCompleted,
        });
      }

      setLastQueryString(currentQueryString);
    } else {
      if (lastQueryString) {
        clearBoomFilter();
        setLastQueryString("");
        resetPaginationAndQueryState({
          setExpandedCells,
          setCurrentPage,
          setTotalDocuments,
          setIsLoadingPage,
          setPageCursors,
          setLastDocumentId,
          setHasNextPage,
          setLastPageOffset,
          setDisplayResults,
          setQueryCompleted,
        });
      }
    }
  }, [hasValidQuery, getFormattedMongoQuery, lastQueryString, dispatch]);

  useEffect(() => {
    const newCollection =
      filter_stream === "ZTF"
        ? "ZTF_alerts"
        : filter_stream === "LSST"
          ? "LSST_alerts"
          : "";

    if (
      newCollection !== selectedCollection &&
      newCollection !== "" &&
      selectedCollection !== ""
    ) {
      setSelectedCollection(newCollection);
      clearBoomFilter();
      resetPaginationAndQueryState({
        setExpandedCells,
        setCurrentPage,
        setTotalDocuments,
        setIsLoadingPage,
        setPageCursors,
        setLastDocumentId,
        setHasNextPage,
        setLastPageOffset,
        setDisplayResults,
        setQueryCompleted,
      });
    } else if (selectedCollection === "" && newCollection !== "") {
      setSelectedCollection(newCollection);
    }
  }, [filter_stream, selectedCollection, dispatch]);

  const defaultStartDate = new Date();
  const defaultEndDate = new Date();
  defaultEndDate.setDate(defaultEndDate.getDate() + 1);

  const { getValues, control, watch } = useForm({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  } as any);

  // Watch for date changes and validate
  const watchedStartDate = watch("startDate" as any);
  const watchedEndDate = watch("endDate" as any);

  useEffect(() => {
    if (watchedStartDate && watchedEndDate) {
      const startDate = new Date(watchedStartDate);
      const endDate = new Date(watchedEndDate);

      if (startDate > endDate) {
        setDateValidationError("Start date must be before end date.");
      } else {
        const diffInMs = endDate.getTime() - startDate.getTime();
        const diffInDays = diffInMs / (1000 * 60 * 60 * 24);

        if (diffInDays > 7) {
          setDateValidationError("Date range cannot exceed 7 days.");
        } else {
          setDateValidationError(null);
        }
      }
    } else {
      setDateValidationError(null);
    }
  }, [watchedStartDate, watchedEndDate]);

  const handleStageToggle = (stageIndex: number) => {
    setExpandedStages((prev: Set<any>) => {
      const newSet = new Set(prev);
      if (newSet.has(stageIndex)) {
        newSet.delete(stageIndex);
      } else {
        newSet.add(stageIndex);
      }
      return newSet;
    });
  };

  useEffect(() => {
    if (mongoDialog?.open) {
      loadCollections();
      resetPaginationAndQueryState({
        setExpandedCells,
        setCurrentPage,
        setTotalDocuments,
        setIsLoadingPage,
        setPageCursors,
        setLastDocumentId,
        setHasNextPage,
        setLastPageOffset,
        setDisplayResults,
        setQueryCompleted,
      });
    }
  }, [mongoDialog?.open]);

  const loadCollections = async () => {
    try {
      setConnectionStatus("connected");
    } catch (error) {
      console.error("Failed to load collections:", error);
      setConnectionStatus("disconnected");
    }
  };

  const handleClose = () => {
    setMongoDialog({ open: false });
    setQueryError(null);
    setShowPipeline(true);
    setPipelineView("complete");
    setExpandedStages(new Set());

    resetPaginationAndQueryState({
      setExpandedCells,
      setCurrentPage,
      setTotalDocuments,
      setIsLoadingPage,
      setPageCursors,
      setLastDocumentId,
      setHasNextPage,
      setLastPageOffset,
      setDisplayResults,
    });
  };

  const handleCopy = async () => {
    try {
      const query = getFormattedMongoQuery();
      await navigator.clipboard.writeText(query);
      setCopySuccess(true);
    } catch (err) {
      console.error("Failed to copy query:", err);
      const textArea = document.createElement("textarea");
      textArea.value = getFormattedMongoQuery();
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopySuccess(true);
    }
  };

  const handleCopyStage = async (stageName: string, stageContent: any) => {
    try {
      const stageObject = { [stageName]: stageContent };
      const formattedStage = JSON.stringify(stageObject, null, 2);
      await navigator.clipboard.writeText(formattedStage);
      setCopySuccess(true);
    } catch (err) {
      console.error("Failed to copy stage:", err);
      const stageObject = { [stageName]: stageContent };
      const formattedStage = JSON.stringify(stageObject, null, 2);
      const textArea = document.createElement("textarea");
      textArea.value = formattedStage;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopySuccess(true);
    }
  };

  const handleDownloadResults = () => {
    if (!displayResults.data || displayResults.data.length === 0) {
      return;
    }

    const jsonString = JSON.stringify(displayResults.data, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    link.download = `query-results-${timestamp}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const executeQuery = async (
    countOnly = false,
    cursor: any = null,
    direction = "forward",
    limit = pageSize + 1,
  ): Promise<any> => {
    const { startDate, endDate } = getConvertedDatesFromForm(getValues);

    const userPipeline = generateMongoQuery();

    let additionalStages: any[] = [];

    const pipeline = combineWithPipeline(
      userPipeline,
      additionalStages,
      countOnly,
    );

    const sortOrder = direction === "backward" ? "Descending" : "Ascending";
    const result: any = countOnly
      ? await runBoomFilter({
          pipeline: pipeline,
          selectedCollection: selectedCollection,
          start_jd: startDate,
          end_jd: endDate,
          filter_id: filter_id,
        })
      : await runBoomFilter({
          pipeline: pipeline,
          selectedCollection: selectedCollection,
          start_jd: startDate,
          end_jd: endDate,
          filter_id: filter_id,
          sort_by: "_id",
          sort_order: sortOrder,
          limit: limit,
          cursor: cursor,
        });

    if (countOnly) {
      return {
        result: result,
        hasNext: false,
        nextCursor: null,
      };
    }
    if (result.data?.data) {
      const originalData = result?.data?.data?.results;
      if (!originalData || originalData.length === 0) {
        setDisplayResults({ data: [] });
        return {
          result: result,
          hasNext: false,
          nextCursor: null,
          firstId: null,
          lastId: null,
        };
      }
      let hasMore = originalData.length > pageSize;
      let data;

      if (direction === "backward") {
        data = hasMore ? originalData.slice(0, pageSize + 1) : originalData;
        data = [...data].reverse();
      } else {
        data = hasMore ? originalData.slice(0, pageSize + 1) : originalData;
      }

      const processedResult = {
        ...result,
        data: {
          ...result.data,
          data: data,
        },
      };

      if (!countOnly) {
        setDisplayResults({ data: data });
      }

      // Store the actual displayed data boundaries for cursor navigation
      const firstId = data.length > 0 ? data[0]._id : null;
      const lastId = data.length > 0 ? data[data.length - 1]._id : null;

      return {
        result: processedResult,
        hasNext: hasMore,
        nextCursor: lastId,
        firstId: firstId,
        lastId: lastId,
        data: data, // Return data for caching
      };
    }
    return {
      result: result,
      hasNext: false,
      nextCursor: null,
      firstId: null,
      lastId: null,
    };
  };

  const handleRunQuery = async () => {
    // Validate date range before running the query
    const { startDate, endDate } = getConvertedDatesFromForm(getValues);
    if (startDate && endDate) {
      const diffInMs = endDate - startDate;
      const diffInDays = diffInMs / (1000 * 60 * 60 * 24);

      if (diffInDays > 7) {
        setQueryError(
          "Date range cannot exceed 7 days. Please select a shorter time period.",
        );
        return;
      }
    }

    setIsRunning(true);
    setQueryError(null);

    resetPaginationAndQueryState({
      setExpandedCells,
      setCurrentPage,
      setTotalDocuments,
      setIsLoadingPage,
      setPageCursors,
      setLastDocumentId,
      setHasNextPage,
      setLastPageOffset,
      setDisplayResults,
      setQueryCompleted,
    });

    try {
      clearBoomFilter();

      // Get first page data first
      const firstPageQueryResult = await executeQuery(false);

      setHasNextPage(firstPageQueryResult.hasNext);

      const newCursors = new Map();
      if (firstPageQueryResult.firstId && firstPageQueryResult.lastId) {
        newCursors.set(1, {
          firstId: firstPageQueryResult.firstId,
          lastId: firstPageQueryResult.lastId,
        });
      }

      setPageCursors(newCursors);

      // Cache page 1 data
      if (firstPageQueryResult.data) {
        const newCache = new Map();
        newCache.set(1, firstPageQueryResult.data);
        setPageDataCache(newCache);
      }

      // Get actual count after first page
      const countQueryResult = await executeQuery(true);
      // Good code when using queries/count endpoint
      // const actualCount = countQueryResult.result?.data?.data || 0;
      // temporary code to get count from results length
      const actualCount = countQueryResult.result?.data?.data?.count;
      setTotalDocuments(actualCount);

      // Set query completed only after both queries are done
      setQueryCompleted(true);
    } catch (error) {
      console.error("Query error:", error);
      setQueryError((error as any).message);
    } finally {
      setIsRunning(false);
    }
  };

  const handlePageChange = async (_event: any, newPage: number) => {
    setIsLoadingPage(true);
    setExpandedCells(new Set());

    try {
      if (pageDataCache.has(newPage)) {
        const cachedData = pageDataCache.get(newPage);
        setDisplayResults({ data: cachedData });
        setCurrentPage(newPage);
        cachedData.length < pageSize + 1
          ? setHasNextPage(false)
          : setHasNextPage(true);
        setIsLoadingPage(false);
        return;
      }

      const isSequential = Math.abs(newPage - currentPage) === 1;

      if (isSequential) {
        let cursor = null;
        let direction = "forward";

        if (newPage > currentPage) {
          const currentPageData = pageCursors.get(currentPage);
          cursor = currentPageData?.lastId;
          direction = "forward";
        } else if (newPage < currentPage) {
          const currentPageData = pageCursors.get(currentPage);
          cursor = currentPageData?.firstId;
          direction = "backward";
        }

        const queryResult = await executeQuery(false, cursor, direction);
        setHasNextPage(queryResult.hasNext);

        const newCursors = new Map(pageCursors);
        if (queryResult.firstId && queryResult.lastId) {
          newCursors.set(newPage, {
            firstId: queryResult.firstId,
            lastId: queryResult.lastId,
          });
        }
        setPageCursors(newCursors);

        if (queryResult.data) {
          const newCache = new Map(pageDataCache);
          newCache.set(newPage, queryResult.data);
          setPageDataCache(newCache);
        }

        setCurrentPage(newPage);
      } else {
        const lastPageOffsetCalc = totalDocuments - (newPage - 1) * pageSize;
        const countQueryResult = await executeQuery(
          false,
          null,
          "backward",
          lastPageOffsetCalc,
        );

        setHasNextPage(countQueryResult.hasNext);

        const newCursors = new Map(pageCursors);
        if (countQueryResult.firstId && countQueryResult.lastId) {
          newCursors.set(newPage, {
            firstId: countQueryResult.firstId,
            lastId: countQueryResult.lastId,
          });
        }
        setPageCursors(newCursors);

        if (countQueryResult.data) {
          const newCache = new Map(pageDataCache);
          newCache.set(newPage, countQueryResult.data);
          setPageDataCache(newCache);
        }

        setLastPageOffset(lastPageOffsetCalc);
        setCurrentPage(newPage);
      }
    } catch (error) {
      console.error("Page change error:", error);
      setQueryError((error as any).message);
    } finally {
      setIsLoadingPage(false);
    }
  };

  const handleSnackbarClose = () => {
    setCopySuccess(false);
  };

  if (!mongoDialog?.open) {
    return null;
  }

  const pipeline = generateMongoQuery();
  const isValid = hasValidQuery();

  return (
    <>
      <Dialog
        open={mongoDialog.open}
        onClose={handleClose}
        maxWidth="lg"
        fullWidth
        slotProps={{
          paper: { sx: { minHeight: "500px", maxHeight: "90vh" } },
        }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="h6" component="div">
              MongoDB Aggregation Pipeline
            </Typography>
            {connectionStatus === "connected" && (
              <Chip label="Connected" color="success" size="small" />
            )}
            {connectionStatus === "disconnected" && (
              <Chip label="Disconnected" color="error" size="small" />
            )}
          </Box>
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent dividers>
          {!isValid ? (
            <Box sx={{ textAlign: "center", py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No filters defined. Add some conditions to generate a MongoDB
                query.
              </Typography>
            </Box>
          ) : (
            <Box>
              {/* Connection Warning */}
              {connectionStatus === "disconnected" && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                  <Typography variant="subtitle2">
                    MongoDB Connection Issue
                  </Typography>
                  <Typography variant="body2">
                    Unable to connect to MongoDB. Make sure MongoDB is running
                    on localhost:27017 and the backend server is started.
                  </Typography>
                </Alert>
              )}
              <form>
                <div>
                  {dateValidationError && (
                    <FormValidationError message={dateValidationError} />
                  )}

                  {/* Date Range Instructions */}
                  <Box sx={{ mb: 2 }}>
                    <Typography
                      variant="subtitle2"
                      color="text.primary"
                      sx={{ mb: 0.5 }}
                    >
                      Select Time Range for Query
                    </Typography>
                  </Box>

                  <div className={classes.timeRange}>
                    <Controller
                      render={({ field: { onChange, value } }: any) => (
                        <LocalizationProvider dateAdapter={AdapterDateFns}>
                          <DateTimePicker
                            value={value}
                            onChange={(newValue: any) => onChange(newValue)}
                            label="Start (Local Time)"
                            {...({ showTodayButton: false } as any)}
                            ampm={useAMPM}
                            slotProps={{ textField: { variant: "outlined" } }}
                          />
                        </LocalizationProvider>
                      )}
                      // rules={{ validate: validateDates }}
                      name={"startDate" as any}
                      control={control}
                      defaultValue={defaultStartDate as any}
                    />
                    <Controller
                      render={({ field: { onChange, value } }: any) => (
                        <LocalizationProvider dateAdapter={AdapterDateFns}>
                          <DateTimePicker
                            value={value}
                            onChange={(newValue: any) => onChange(newValue)}
                            label="End (Local Time)"
                            {...({ showTodayButton: false } as any)}
                            ampm={useAMPM}
                            slotProps={{ textField: { variant: "outlined" } }}
                          />
                        </LocalizationProvider>
                      )}
                      // rules={{ validate: validateDates }}
                      name={"endDate" as any}
                      control={control}
                      defaultValue={defaultEndDate as any}
                    />
                  </div>
                </div>

                {/* Collection Selector and Run Controls */}
                <Box
                  sx={{ display: "flex", gap: 2, mb: 3, alignItems: "center" }}
                >
                  <Button
                    variant="contained"
                    color="primary"
                    type="button"
                    startIcon={
                      isRunning ? <CircularProgress size={16} /> : <RunIcon />
                    }
                    onClick={handleRunQuery}
                    disabled={
                      isRunning ||
                      connectionStatus === "disconnected" ||
                      !!dateValidationError
                    }
                    sx={{ minWidth: 120 }}
                  >
                    {isRunning ? "Running..." : "Run Query"}
                  </Button>
                </Box>
              </form>

              {/* Query Error Display */}
              {queryError && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  <Typography variant="subtitle2">Query Error:</Typography>
                  <Typography variant="body2">{queryError}</Typography>
                </Alert>
              )}

              {/* Query Results */}
              {((displayResults.data?.length ?? 0) > 0 || queryCompleted) && (
                <Box sx={{ mb: 3 }}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      mb: 2,
                    }}
                  >
                    <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
                      Query Results
                    </Typography>
                    <Chip
                      label={
                        queryCompleted && totalDocuments === 0
                          ? "0 documents"
                          : queryCompleted
                            ? `${totalDocuments} documents`
                            : "Loading..."
                      }
                      size="small"
                      color={
                        queryCompleted && totalDocuments === 0
                          ? "default"
                          : queryCompleted
                            ? "success"
                            : "primary"
                      }
                    />
                    {totalDocuments > pageSize &&
                      (displayResults.data?.length ?? 0) > 0 && (
                        <Chip
                          label={`Page ${currentPage} of ${Math.ceil(
                            totalDocuments / pageSize,
                          )}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    <IconButton
                      size="small"
                      onClick={handleDownloadResults}
                      disabled={!displayResults.data?.length}
                      title="Download results as JSON"
                    >
                      <DownloadIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => setIsFullscreen(true)}
                      disabled={!displayResults.data?.length}
                    >
                      <FullscreenIcon />
                    </IconButton>
                  </Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 2 }}
                  >
                    Generated query results — not all alert fields are shown.
                  </Typography>
                  {(displayResults.data?.length ?? 0) > 0 ? (
                    <>
                      <TableContainer
                        component={Paper}
                        sx={{
                          maxHeight: 400,
                          overflow: "auto",
                          width: "100%",
                          "& .MuiTable-root": {
                            minWidth: "100%",
                            width: "max-content",
                            tableLayout: "auto",
                          },
                          "&::-webkit-scrollbar": {
                            width: 8,
                            height: 8,
                          },
                          "&::-webkit-scrollbar-track": {
                            backgroundColor: "rgba(0,0,0,0.1)",
                          },
                          "&::-webkit-scrollbar-thumb": {
                            backgroundColor: "rgba(0,0,0,0.3)",
                            borderRadius: 4,
                          },
                        }}
                      >
                        <Table
                          size="small"
                          stickyHeader
                          sx={{
                            tableLayout: "auto",
                            width: "max-content",
                            minWidth: "100%",
                          }}
                        >
                          <TableHead>
                            <TableRow>
                              {Object.keys(displayResults.data?.[0] || {})
                                .filter((key) => key !== "_id")
                                .map((key) => (
                                  <TableCell
                                    key={key}
                                    sx={{
                                      fontWeight: "bold",
                                      minWidth: 150,
                                      whiteSpace: "nowrap",
                                      position: "sticky",
                                      top: 0,
                                      backgroundColor: "background.paper",
                                      zIndex: 1,
                                    }}
                                  >
                                    {key}
                                  </TableCell>
                                ))}
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {displayResults?.data
                              ?.slice(0, 50)
                              .map((row: any, rowIndex: number) => (
                                <TableRow
                                  key={rowIndex}
                                  sx={{
                                    height: "auto",
                                    minHeight: "fit-content",
                                    "& .MuiTableCell-root": {
                                      height: "auto",
                                      minHeight: "fit-content",
                                    },
                                  }}
                                >
                                  {Object.entries(row)
                                    .filter(([key]) => key !== "_id")
                                    .map(
                                      (
                                        [key, value]: any,
                                        cellIndex: number,
                                      ) => {
                                        const cellKey = `${rowIndex}-${cellIndex}`;
                                        const isJsonExpanded =
                                          expandedCells.has(cellKey);
                                        const hasJsonContent =
                                          typeof value === "object";
                                        const isObjectId =
                                          key === "objectId" &&
                                          typeof value === "string";

                                        return (
                                          <TableCell
                                            key={cellIndex}
                                            sx={{
                                              verticalAlign: "top",
                                              minWidth: hasJsonContent
                                                ? isJsonExpanded
                                                  ? 300
                                                  : 150
                                                : 100,
                                              maxWidth: hasJsonContent
                                                ? isJsonExpanded
                                                  ? 600
                                                  : 300
                                                : 200,
                                              width: hasJsonContent
                                                ? isJsonExpanded
                                                  ? "auto"
                                                  : "auto"
                                                : "auto",
                                              padding: 1,
                                              borderRight: "1px solid",
                                              borderColor: "divider",
                                              transition: "all 0.3s ease",
                                              overflow: "visible",
                                              height: "auto",
                                              minHeight: "fit-content",
                                            }}
                                          >
                                            {hasJsonContent ? (
                                              <Box
                                                sx={{
                                                  minWidth: isJsonExpanded
                                                    ? 250
                                                    : 150,
                                                  maxWidth: isJsonExpanded
                                                    ? 550
                                                    : 350,
                                                  width: "100%",
                                                  minHeight: "fit-content",
                                                  height: "auto",
                                                  overflow: "visible",
                                                  "& .react-json-view": {
                                                    height: "auto !important",
                                                    minHeight: "fit-content",
                                                  },
                                                }}
                                              >
                                                <ReactJson
                                                  src={value}
                                                  name={false}
                                                  collapsed={
                                                    key === "annotations"
                                                      ? false
                                                      : !isJsonExpanded
                                                  }
                                                  displayDataTypes={false}
                                                  displayObjectSize={false}
                                                  enableClipboard={false}
                                                  style={{
                                                    height: "auto",
                                                    minHeight: "fit-content",
                                                    lineHeight: "1.4",
                                                    fontSize: "12px",
                                                  }}
                                                />
                                              </Box>
                                            ) : isObjectId ? (
                                              <Link
                                                href={`https://babamul.caltech.edu/objects/${filter_stream.toUpperCase()}/${value}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                              >
                                                <Typography
                                                  variant="body2"
                                                  sx={{
                                                    fontFamily: "monospace",
                                                    wordBreak: "break-word",
                                                  }}
                                                >
                                                  {String(value)}
                                                </Typography>
                                              </Link>
                                            ) : (
                                              <Typography
                                                variant="body2"
                                                sx={{
                                                  fontFamily: "monospace",
                                                  wordBreak: "break-word",
                                                }}
                                              >
                                                {String(value)}
                                              </Typography>
                                            )}
                                          </TableCell>
                                        );
                                      },
                                    )}
                                </TableRow>
                              ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                      {/* Always show pagination info when there are results */}
                      {(displayResults.data?.length ?? 0) > 0 && (
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "center",
                            mt: 2,
                          }}
                        >
                          <Stack spacing={2}>
                            {/* Cursor-based pagination controls - show if there are multiple pages OR if hasNext is true OR if results exist */}
                            {(totalDocuments > pageSize ||
                              hasNextPage ||
                              currentPage > 1 ||
                              (displayResults.data?.length ?? 0) >=
                                pageSize) && (
                              <Box
                                sx={{
                                  display: "flex",
                                  justifyContent: "center",
                                  gap: 1,
                                  alignItems: "center",
                                }}
                              >
                                <IconButton
                                  onClick={(e: any) => handlePageChange(e, 1)}
                                  disabled={currentPage <= 1 || isLoadingPage}
                                  size="small"
                                  title="First page"
                                >
                                  <FirstPageIcon />
                                </IconButton>

                                <IconButton
                                  onClick={(e: any) =>
                                    handlePageChange(e, currentPage - 1)
                                  }
                                  disabled={currentPage <= 1 || isLoadingPage}
                                  size="small"
                                  title="Previous page"
                                >
                                  <ChevronLeftIcon />
                                </IconButton>

                                <Typography
                                  variant="body2"
                                  sx={{ minWidth: 80, textAlign: "center" }}
                                >
                                  Page {currentPage}
                                </Typography>

                                <IconButton
                                  onClick={(e: any) =>
                                    handlePageChange(e, currentPage + 1)
                                  }
                                  disabled={!hasNextPage || isLoadingPage}
                                  size="small"
                                  title="Next page"
                                >
                                  <ChevronRightIcon />
                                </IconButton>

                                <IconButton
                                  onClick={(e: any) =>
                                    handlePageChange(
                                      e,
                                      Math.ceil(totalDocuments / pageSize),
                                    )
                                  }
                                  disabled={
                                    !hasNextPage ||
                                    isLoadingPage ||
                                    totalDocuments === 0
                                  }
                                  size="small"
                                  title="Last page"
                                >
                                  <LastPageIcon />
                                </IconButton>
                              </Box>
                            )}

                            <Typography
                              variant="caption"
                              sx={{
                                textAlign: "center",
                                color: "text.secondary",
                              }}
                            >
                              {isLoadingPage
                                ? "Loading..."
                                : totalDocuments > 0
                                  ? `Showing page ${currentPage} (${Math.min(
                                      displayResults.data?.length || 0,
                                      pageSize,
                                    )} results on this page)`
                                  : `Showing ${Math.min(
                                      displayResults.data?.length || 0,
                                      pageSize,
                                    )} results (cursor-based pagination)`}
                            </Typography>
                          </Stack>
                        </Box>
                      )}
                    </>
                  ) : (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ p: 2, textAlign: "center" }}
                    >
                      No documents matched the query
                    </Typography>
                  )}

                  <Divider sx={{ my: 2 }} />
                </Box>
              )}

              {/* Pipeline Visualization */}
              <PipelineViewer
                pipeline={pipeline}
                showPipeline={showPipeline}
                setShowPipeline={setShowPipeline}
                pipelineView={pipelineView}
                setPipelineView={setPipelineView}
                expandedStages={expandedStages}
                handleStageToggle={handleStageToggle}
                handleCopy={handleCopy}
                handleCopyStage={handleCopyStage}
              />
            </Box>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={copySuccess}
        autoHideDuration={3000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity="success"
          variant="filled"
        >
          MongoDB query copied to clipboard!
        </Alert>
      </Snackbar>

      <FullscreenResultsDialog
        isFullscreen={isFullscreen}
        setIsFullscreen={setIsFullscreen}
        displayResults={displayResults}
        queryCompleted={queryCompleted}
        totalDocuments={totalDocuments}
        currentPage={currentPage}
        pageSize={pageSize}
        hasNextPage={hasNextPage}
        isLoadingPage={isLoadingPage}
        expandedCells={expandedCells}
        handlePageChange={handlePageChange}
        handleDownloadResults={handleDownloadResults}
      />
    </>
  );
};

export default MongoQueryDialog;

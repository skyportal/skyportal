import { useState, useEffect, useRef } from "react";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
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
  Link,
  TextField,
  Autocomplete,
} from "@mui/material";
import {
  Close as CloseIcon,
  PlayArrow as RunIcon,
  Fullscreen as FullscreenIcon,
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
import {
  RunBoomFilterArg,
  useRunBoomFilterMutation,
} from "../../../../ducks/boom_run_filter";
import { useGetProfileQuery } from "../../../../ducks/profile";
import { useGetGcnEventsQuery } from "../../../../ducks/gcnEvents";
import PipelineViewer from "./PipelineViewer";
import FullscreenResultsDialog from "./FullscreenResultsDialog";

dayjs.extend(utc);

const DEFAULT_MAX_RESULTS = 50;
const MAX_RESULTS_LIMIT = 200;
// Matches DEFAULTS["credible_level"] in skyportal/utils/gcn_crossmatch.py, so a
// preview searches the same region the crossmatch service does.
const DEFAULT_CREDIBLE_LEVEL = 90;
const GCN_EVENT_PAGE_SIZE = 100;
const NARROW_HINT = "Narrow the time window or the filter.";
const ALERT_COLLECTIONS: Record<string, string> = {
  ZTF: "ZTF_alerts",
  LSST: "LSST_alerts",
  DECAM: "DECAM_alerts",
};

const useStyles = makeStyles()((_theme) => ({
  timeRange: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.5rem",
    marginBottom: "1rem",
  },
}));

const combineWithPipeline = (
  userPipeline: any[],
  additionalStages: any[] = [],
  _isCountOnly = false,
) => {
  const finalPipeline: any[] = [];

  finalPipeline.push(...userPipeline);

  if (additionalStages && additionalStages.length > 0) {
    finalPipeline.unshift(...additionalStages);
  }

  return finalPipeline;
};

// A percentage, so the whole sky is 100 and anything above it is a typo.
const parseCredibleLevel = (value: string) => {
  const n = Number(value);
  return value.trim() !== "" && Number.isInteger(n) && n >= 1 && n <= 100
    ? n
    : null;
};

const parseMaxResults = (value: string) => {
  const n = Number(value);
  return value.trim() !== "" &&
    Number.isInteger(n) &&
    n >= 1 &&
    n <= MAX_RESULTS_LIMIT
    ? n
    : null;
};

const jdOf = (row: any) => row?.candidate?.jd ?? row?.jd ?? -Infinity;

// Newest first, so the table is stable: the broker returns matches unordered.
const byJdDescending = (a: any, b: any) =>
  jdOf(b) - jdOf(a) || String(a?._id).localeCompare(String(b?._id));

const previewErrorMessage = (error: any) => {
  const detail =
    error?.status === "PARSING_ERROR"
      ? null
      : typeof error?.error === "string"
        ? error.error
        : error?.data?.message;
  return `The preview failed or timed out. ${NARROW_HINT}${
    detail ? ` (${detail})` : ""
  }`;
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
  });
  const [selectedCollection, setSelectedCollection] = useState(
    ALERT_COLLECTIONS[filter_stream?.toUpperCase() ?? ""] ?? "",
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
  const [queryCompleted, setQueryCompleted] = useState(false);
  const [lastQueryString, setLastQueryString] = useState("");
  const [maxResultsInput, setMaxResultsInput] = useState(
    String(DEFAULT_MAX_RESULTS),
  );
  const [hasMore, setHasMore] = useState(false);
  const [gcnEvent, setGcnEvent] = useState<any>(null);
  const [gcnEventSearch, setGcnEventSearch] = useState("");
  const [credibleLevelInput, setCredibleLevelInput] = useState(
    String(DEFAULT_CREDIBLE_LEVEL),
  );
  const [lastRunArgs, setLastRunArgs] = useState<RunBoomFilterArg | null>(null);
  const [exactCount, setExactCount] = useState<{
    loading?: boolean;
    count?: number;
    error?: string;
  }>({});
  // Bumped on every reset so a count from a previous run is not shown.
  const runId = useRef(0);

  const maxResults = parseMaxResults(maxResultsInput);
  const gcnEvents: any[] =
    useGetGcnEventsQuery(
      { numPerPage: GCN_EVENT_PAGE_SIZE, partialdateobs: gcnEventSearch },
      { skip: !mongoDialog?.open },
    ).data?.events ?? [];
  const credibleLevel = parseCredibleLevel(credibleLevelInput);

  const resetQueryState = () => {
    runId.current += 1;
    setExpandedCells(new Set());
    setDisplayResults({ data: [] });
    setHasMore(false);
    setLastRunArgs(null);
    setExactCount({});
    setQueryCompleted(false);
  };

  useEffect(() => {
    if (hasValidQuery()) {
      const currentQueryString = getFormattedMongoQuery();

      if (lastQueryString && lastQueryString !== currentQueryString) {
        clearBoomFilter();
        resetQueryState();
      }

      setLastQueryString(currentQueryString);
    } else {
      if (lastQueryString) {
        clearBoomFilter();
        setLastQueryString("");
        resetQueryState();
      }
    }
  }, [hasValidQuery, getFormattedMongoQuery, lastQueryString, dispatch]);

  useEffect(() => {
    const newCollection =
      ALERT_COLLECTIONS[filter_stream?.toUpperCase() ?? ""] ?? "";

    if (
      newCollection !== selectedCollection &&
      newCollection !== "" &&
      selectedCollection !== ""
    ) {
      setSelectedCollection(newCollection);
      clearBoomFilter();
      resetQueryState();
    } else if (selectedCollection === "" && newCollection !== "") {
      setSelectedCollection(newCollection);
    }
  }, [filter_stream, selectedCollection, dispatch]);

  const defaultStartDate = new Date();
  defaultStartDate.setDate(defaultStartDate.getDate() - 1);
  const defaultEndDate = new Date();

  const { getValues, setValue, control, watch } = useForm({
    startDate: defaultStartDate,
    endDate: defaultEndDate,
  } as any);

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
      resetQueryState();
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

  const selectGcnEvent = (event: any) => {
    setGcnEvent(event);
    if (event?.dateobs) {
      const dateobs = dayjs.utc(event.dateobs);
      setValue("startDate" as any, dateobs.toDate() as any);
      setValue("endDate" as any, dateobs.add(7, "day").toDate() as any);
    }
  };

  const handleClose = () => {
    setMongoDialog({ open: false });
    setQueryError(null);
    setShowPipeline(true);
    setPipelineView("complete");
    setExpandedStages(new Set());

    resetQueryState();
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

  const handleRunQuery = async () => {
    const { startDate, endDate } = getConvertedDatesFromForm(getValues);
    // BOOM rejects a query without a date window with a 400.
    if (!startDate || !endDate) {
      setQueryError("Select a start and end date before running the query.");
      return;
    }
    if (endDate - startDate > 7) {
      setQueryError(
        "Date range cannot exceed 7 days. Please select a shorter time period.",
      );
      return;
    }
    if (maxResults === null) return;

    setIsRunning(true);
    setQueryError(null);
    resetQueryState();
    clearBoomFilter();
    const id = runId.current;

    const args: RunBoomFilterArg = {
      pipeline: combineWithPipeline(generateMongoQuery()),
      selectedCollection: selectedCollection,
      start_jd: startDate,
      end_jd: endDate,
      filter_id: filter_id,
      // Only sent when an event is chosen: the backend reads the region from
      // dateobs, and sending none leaves the preview searching the whole sky.
      ...(gcnEvent?.dateobs
        ? {
            dateobs: gcnEvent.dateobs,
            credible_level: credibleLevel ?? DEFAULT_CREDIBLE_LEVEL,
          }
        : {}),
    };
    try {
      // No sort, so BOOM can stop at the limit; the extra row says whether
      // more matches exist without a full count.
      const result = await runBoomFilter({
        ...args,
        unsorted: true,
        limit: maxResults + 1,
      }).unwrap();
      if (id !== runId.current) return;
      const rows: any[] = result?.results ?? [];
      setHasMore(rows.length > maxResults);
      setDisplayResults({
        data: rows.slice(0, maxResults).sort(byJdDescending),
      });
      setLastRunArgs(args);
      setQueryCompleted(true);
    } catch (error) {
      console.error("Query error:", error);
      if (id === runId.current) setQueryError(previewErrorMessage(error));
    } finally {
      setIsRunning(false);
    }
  };

  // The count scans the whole window, so it is only run on request.
  const handleExactCount = async () => {
    if (!lastRunArgs) return;
    const id = runId.current;
    setExactCount({ loading: true });
    try {
      const result = await runBoomFilter(lastRunArgs).unwrap();
      if (id === runId.current) setExactCount({ count: result?.count });
    } catch (error) {
      console.error("Count error:", error);
      if (id === runId.current) {
        setExactCount({ error: `Too many to count. ${NARROW_HINT}` });
      }
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
  const resultCount = displayResults.data?.length ?? 0;
  const summary = hasMore
    ? `Showing first ${resultCount} matches (more exist)`
    : `${resultCount} ${resultCount === 1 ? "match" : "matches"}`;

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
                      name={"endDate" as any}
                      control={control}
                      defaultValue={defaultEndDate as any}
                    />
                  </div>
                </div>

                <Box
                  sx={{
                    display: "flex",
                    gap: 2,
                    mb: 3,
                    alignItems: "flex-start",
                  }}
                >
                  <Autocomplete
                    options={gcnEvents}
                    value={gcnEvent}
                    onChange={(_e, value) => selectGcnEvent(value)}
                    onInputChange={(_e, value, reason) => {
                      if (reason === "input" || reason === "clear") {
                        setGcnEventSearch(value);
                      }
                    }}
                    filterOptions={(options) => options}
                    getOptionLabel={(option: any) =>
                      option?.aliases?.length
                        ? `${option.aliases[0]} (${option.dateobs})`
                        : (option?.dateobs ?? "")
                    }
                    isOptionEqualToValue={(option: any, value: any) =>
                      option?.dateobs === value?.dateobs
                    }
                    size="small"
                    sx={{ width: 320 }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="GCN event (optional)"
                        helperText={
                          gcnEvent
                            ? "Alerts inside this event's credible region"
                            : "All sky"
                        }
                      />
                    )}
                  />
                  <TextField
                    label="Credible level"
                    type="number"
                    size="small"
                    value={credibleLevelInput}
                    onChange={(e) => setCredibleLevelInput(e.target.value)}
                    disabled={!gcnEvent}
                    error={!!gcnEvent && credibleLevel === null}
                    helperText={
                      gcnEvent && credibleLevel === null
                        ? "Enter a whole percentage from 1 to 100"
                        : " "
                    }
                    slotProps={{ htmlInput: { min: 1, max: 100, step: 1 } }}
                    sx={{ width: 150 }}
                  />
                  <TextField
                    label="Max results"
                    type="number"
                    size="small"
                    value={maxResultsInput}
                    onChange={(e) => setMaxResultsInput(e.target.value)}
                    error={maxResults === null}
                    helperText={
                      maxResults === null
                        ? `Enter a whole number from 1 to ${MAX_RESULTS_LIMIT}`
                        : " "
                    }
                    slotProps={{
                      htmlInput: { min: 1, max: MAX_RESULTS_LIMIT, step: 1 },
                    }}
                    sx={{ width: 180 }}
                  />
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
                      !!dateValidationError ||
                      maxResults === null ||
                      (!!gcnEvent && credibleLevel === null)
                    }
                    sx={{ minWidth: 120, height: 40 }}
                  >
                    {isRunning ? "Running..." : "Run Query"}
                  </Button>
                </Box>
              </form>

              {queryError && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  <Typography variant="subtitle2">Query Error:</Typography>
                  <Typography variant="body2">{queryError}</Typography>
                </Alert>
              )}

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
                      label={summary}
                      size="small"
                      color={resultCount === 0 ? "default" : "success"}
                    />
                    {hasMore &&
                      (exactCount.count !== undefined ? (
                        <Chip
                          label={`${exactCount.count} total matches`}
                          size="small"
                          variant="outlined"
                        />
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={handleExactCount}
                          disabled={exactCount.loading}
                          startIcon={
                            exactCount.loading ? (
                              <CircularProgress size={14} />
                            ) : undefined
                          }
                        >
                          Get exact count
                        </Button>
                      ))}
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
                    Rows are sorted by JD, newest first.
                    {hasMore &&
                      ` They are a sample of the matches the broker found first, not the latest ones.`}
                  </Typography>
                  {exactCount.error && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      {exactCount.error}
                    </Alert>
                  )}
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
                            {displayResults?.data?.map(
                              (row: any, rowIndex: number) => (
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
                              ),
                            )}
                          </TableBody>
                        </Table>
                      </TableContainer>
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
        summary={summary}
        expandedCells={expandedCells}
        handleDownloadResults={handleDownloadResults}
      />
    </>
  );
};

export default MongoQueryDialog;

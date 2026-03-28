import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DownloadIcon from "@mui/icons-material/Download";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Dialog from "@mui/material/Dialog";
import MenuItem from "@mui/material/MenuItem";
import Menu from "@mui/material/Menu";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";
import { JSONTree } from "react-json-tree";

import Button from "../Button";

import * as Actions from "../../ducks/gcnEvent";
import AddSurveyEfficiencyObservationPlanPage from "../survey_efficiency/AddSurveyEfficiencyObservationPlanPage";
import AddRunFromObservationPlanPage from "./AddRunFromObservationPlanPage";
import ObservationPlanGlobe from "./ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "./ObservationPlanSummaryStatistics";
import { showNotification } from "baselayer/components/Notifications";

const useStyles = makeStyles(() => ({
  actionButtons: {
    display: "flex",
    alignItems: "center",
    flexDirection: "column",
    gap: "0.3rem",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: `${theme.spacing(0.5)} 0 ${theme.spacing(
              0.5,
            )} ${theme.spacing(0.5)}`,
          },
        },
      },
      MUIDataTableBodyCell: {
        styleOverrides: {
          root: {
            padding: `0 ${theme.spacing(0.5)} 0 ${theme.spacing(0.5)}`,
          },
          stackedCommon: {
            overflow: "hidden",
            "&:last-child": {
              paddingLeft: "0.25rem",
            },
          },
        },
      },
      MUIDataTablePagination: {
        styleOverrides: {
          toolbar: {
            flexFlow: "row wrap",
          },
        },
      },
    },
  });

const ObservationPlanRequestLists = ({ dateobs }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const [anchorEl, setAnchorEl] = useState(null);
  const [fetchedForLocalizationId, setFetchedForLocalizationId] =
    useState(null);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);
  const [showTable, setShowTable] = useState(null);

  const observationPlanRequestList = gcnEvent?.observation_plans || [];

  useEffect(() => {
    if (!gcnEvent?.localizations?.length) return;
    setSelectedLocalizationId(gcnEvent?.localizations[0]?.id);
  }, [gcnEvent]);

  useEffect(() => {
    if (
      gcnEvent &&
      selectedLocalizationId &&
      selectedLocalizationId !== fetchedForLocalizationId
    ) {
      setFetchedForLocalizationId(selectedLocalizationId);
      dispatch(Actions.fetchObservationPlanRequests(gcnEvent.id));
    }
  }, [
    gcnEvent,
    selectedLocalizationId,
    fetchedForLocalizationId,
    dateobs,
    dispatch,
  ]);

  function handleShowTable(id) {
    dispatch(Actions.fetchObservationPlan(id));
    setShowTable(id);
  }

  const [isDeleting, setIsDeleting] = useState(null);
  const handleDelete = async (id) => {
    setIsDeleting(id);
  };

  const [isSubmittingTreasureMap, setIsSubmittingTreasureMap] = useState(null);
  const handleSubmitTreasureMap = async (id) => {
    setIsSubmittingTreasureMap(id);
    await dispatch(Actions.submitObservationPlanRequestTreasureMap(id));
    setIsSubmittingTreasureMap(null);
  };

  const [isDeletingTreasureMap, setIsDeletingTreasureMap] = useState(null);
  const handleDeleteTreasureMap = async (id) => {
    setIsDeletingTreasureMap(id);
    await dispatch(Actions.deleteObservationPlanRequestTreasureMap(id));
    setIsDeletingTreasureMap(null);
  };

  const [isSending, setIsSending] = useState(null);
  const handleSend = async (id) => {
    setIsSending(id);
    await dispatch(Actions.sendObservationPlanRequest(id));
    setIsSending(null);
    setShowTable(null);
  };

  const [isRemoving, setIsRemoving] = useState(null);
  const handleRemove = async (id) => {
    setIsRemoving(id);
    await dispatch(Actions.removeObservationPlanRequest(id));
    setIsRemoving(null);
  };

  const { instrumentList, instrumentObsplanFormParams } = useSelector(
    (state) => state.instruments,
  );

  if (
    !instrumentList?.length ||
    !Object.keys(instrumentObsplanFormParams).length
  ) {
    return <CircularProgress />;
  }

  if (!observationPlanRequestList.length) {
    return <p>No observation plan requests for this event...</p>;
  }

  if (!gcnEvent.localizations?.length || !selectedLocalizationId) {
    return <h3>Fetching skymap...</h3>;
  }

  const instLookUp = Object.fromEntries(instrumentList.map((i) => [i.id, i]));
  observationPlanRequestList.sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at),
  );

  const requestsGroupedByInstId = observationPlanRequestList.reduce((r, a) => {
    r[a.allocation.instrument.id] = [
      ...(r[a.allocation.instrument.id] || []),
      a,
    ];
    return r;
  }, {});

  Object.values(requestsGroupedByInstId).forEach((value) => value.sort());

  const getDataTableColumns = (instrument_id) => {
    const implementsDelete =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.delete;
    const implementsSend =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.send;
    const implementsRemove =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.remove;
    const queueable = implementsSend || implementsRemove;

    const renderPayload = (dataIndex) => {
      const request = requestsGroupedByInstId[instrument_id][dataIndex];
      if (!request?.payload) return null;

      return (
        <Box sx={{ whiteSpace: "nowrap" }}>
          <JSONTree data={request.payload} hideRoot />
        </Box>
      );
    };

    const renderStatus = (dataIndex) => {
      const status =
        instrumentObsplanFormParams[instrument_id][dataIndex]?.status;
      if (!status) return null;
      const colorMap = {
        complete: "success",
        "submitted to telescope queue": "warning",
      };
      return <Chip label={status} color={colorMap[status] || "default"} />;
    };

    const renderSummaryStatistics = (dataIndex) => {
      const request = requestsGroupedByInstId[instrument_id][dataIndex];
      if (request.status === "running") return <CircularProgress />;

      return (
        <Box sx={{ minWidth: "200px" }}>
          <ObservationPlanSummaryStatistics observationPlanRequest={request} />
        </Box>
      );
    };

    const renderSkymap = (dataIndex) => {
      const request = requestsGroupedByInstId[instrument_id][dataIndex];
      if (
        !["complete", "running", "submitted to telescope queue"].includes(
          request?.status,
        )
      ) {
        return null;
      }

      return (
        <Box sx={{ minWidth: "500px" }}>
          <ObservationPlanGlobe observationplanRequest={request} />
        </Box>
      );
    };

    const renderManage = (dataIndex) => {
      const request = requestsGroupedByInstId[instrument_id][dataIndex];
      if (request.status === "running") return <CircularProgress />;

      const downloadLink = (rubinFormat = false) =>
        `/api/observation_plan/${request.id}?includePlannedObservations=True${
          rubinFormat ? "&rubinFormat=True" : ""
        }`;

      const handleRubinDownload = async (rubinFormat) => {
        const response = await fetch(downloadLink(rubinFormat));
        if (!response.ok) {
          const json_response = await response.json();
          dispatch(
            showNotification(
              json_response.message || "Error downloading file",
              "error",
            ),
          );
          return;
        }
        const blob = await response.blob();
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `${rubinFormat ? "rubin-" : ""}observation-plan-${
          request.id
        }.json`;
        link.click();
      };

      return (
        <div className={classes.actionButtons}>
          <Button
            secondary
            href={`/api/observation_plan/${request.id}/gcn`}
            download={`observation-plan-gcn-${request.id}`}
            data-testid={`gcnRequest_${request.id}`}
            endIcon={<DownloadIcon />}
            size="small"
            disabled={!request.observation_plans?.length}
          >
            GCN
          </Button>
          <Button
            secondary
            size="small"
            onClick={(e) => setAnchorEl(e.currentTarget)}
            endIcon={<DownloadIcon />}
          >
            Download
          </Button>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
          >
            <MenuItem
              onClick={async () => {
                setAnchorEl(null);
                await handleRubinDownload(false);
              }}
            >
              ZTF compatible
            </MenuItem>
            <MenuItem
              onClick={async () => {
                setAnchorEl(null);
                await handleRubinDownload(true);
              }}
              disabled={!request.observation_plans?.length}
            >
              Rubin compatible
            </MenuItem>
          </Menu>
          <Button
            secondary
            href={`/api/observation_plan/${request.id}/movie`}
            download={`observation-plan-movie-${request.id}`}
            endIcon={<DownloadIcon />}
            size="small"
            disabled={!request.observation_plans?.length}
          >
            GIF
          </Button>
          <AddRunFromObservationPlanPage observationPlanRequest={request} />
          <AddSurveyEfficiencyObservationPlanPage
            gcnevent={gcnEvent}
            observationPlanRequest={request}
          />
          {implementsDelete && (
            <Button
              primary
              onClick={() => handleDelete(request.id)}
              size="small"
              data-testid={`deleteRequest_${request.id}`}
              disabled={request.status === "submitted to telescope queue"}
              loading={isDeleting === request.id}
            >
              Delete
            </Button>
          )}
        </div>
      );
    };

    const renderQueue = (dataIndex) => {
      if (!queueable) return null;

      const request = requestsGroupedByInstId[instrument_id][dataIndex];
      if (request.status === "running") return <CircularProgress />;

      const plan = request?.observation_plans?.[0];
      const stats = plan?.statistics?.[0]?.statistics;
      if (
        plan &&
        ["complete", "submitted to telescope queue"].includes(plan.status) &&
        stats?.num_observations === 0
      ) {
        return <div> No observations planned. </div>;
      }
      return (
        <div>
          {implementsSend && request.status === "complete" && (
            <Button
              primary
              onClick={() => handleShowTable(request.id)}
              size="small"
              loading={isSending === request.id}
              sx={{ marginBottom: "0.2rem" }}
            >
              Send to Queue
            </Button>
          )}
          {implementsRemove &&
            request.status === "submitted to telescope queue" && (
              <Button
                secondary
                onClick={() => handleRemove(request.id)}
                size="small"
                loading={isRemoving === request.id}
                sx={{ marginBottom: "0.2rem" }}
              >
                Remove from Queue
              </Button>
            )}
          <Dialog
            open={showTable === request.id}
            onClose={() => setShowTable(null)}
            sx={{ minWidth: "60vw" }}
          >
            <DialogTitle>Observation plan</DialogTitle>
            <DialogContent>
              {gcnEvent?.observation_plan?.id === request.id ? (
                <>
                  <MUIDataTable // Display observations in chronological order
                    data={
                      gcnEvent.observation_plan.observation_plans?.[0]
                        ?.planned_observations || []
                    }
                    columns={[
                      { name: "obstime", label: "Time" },
                      { name: "field_id", label: "Field ID" },
                      { name: "filt", label: "Filter" },
                      { name: "exposure_time", label: "Exposure Time" },
                      { name: "weight", label: "Weight" },
                    ]}
                    options={{
                      filter: false,
                      sort: false,
                      print: true,
                      download: true,
                      search: true,
                      selectableRows: "none",
                      enableNestedDataAccess: ".",
                      elevation: 0,
                    }}
                  />
                  <Button
                    primary
                    onClick={() => handleSend(request.id)}
                    size="small"
                  >
                    Send to Queue
                  </Button>
                </>
              ) : (
                <CircularProgress />
              )}
            </DialogContent>
          </Dialog>
        </div>
      );
    };

    const renderTreasureMap = (dataIndex) => {
      const request = requestsGroupedByInstId[instrument_id][dataIndex];
      if (request.status === "running") return <CircularProgress />;

      return (
        <div className={classes.actionButtons}>
          <Button
            secondary
            onClick={() => handleSubmitTreasureMap(request.id)}
            size="small"
            data-testid={`treasuremapRequest_${request.id}`}
            loading={isSubmittingTreasureMap === request.id}
          >
            Send
          </Button>
          <Button
            sx={{ marginBottom: "0.2rem" }}
            secondary
            onClick={() => handleDeleteTreasureMap(request.id)}
            size="small"
            loading={isDeletingTreasureMap === request.id}
          >
            Retract
          </Button>
        </div>
      );
    };

    return [
      { name: "requester.username", label: "Requester" },
      { name: "allocation.group.name", label: "Allocation" },
      {
        name: "payload",
        label: "Payload",
        options: { customBodyRenderLite: renderPayload },
      },
      {
        name: "status",
        label: "Status",
        options: { customBodyRenderLite: renderStatus },
      },
      {
        name: "statistics",
        label: "Summary Statistics",
        options: { customBodyRenderLite: renderSummaryStatistics },
      },
      {
        name: "skymap",
        label: "Skymap",
        options: { customBodyRenderLite: renderSkymap },
      },
      {
        name: "manage",
        label: "Manage",
        options: { customBodyRenderLite: renderManage },
      },
      ...(queueable
        ? [
            {
              name: "queue",
              label: "Telescope Queue",
              options: { customBodyRenderLite: renderQueue },
            },
          ]
        : []),
      {
        name: "treasureMap",
        label: "Treasure Map",
        options: { customBodyRenderLite: renderTreasureMap },
      },
    ];
  };

  const options = {
    filter: false,
    sort: false,
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPageOptions: [1, 10, 15],
  };

  return Object.keys(requestsGroupedByInstId).map((instrument_id) => (
    <Accordion
      sx={{
        width: "99%",
        "&::before": { display: "none" },
        marginBottom: "0.2rem",
      }}
      key={`instrument_${instrument_id}_table_div`}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        data-testid={`${instLookUp[instrument_id].name}-requests-header`}
      >
        <Typography variant="subtitle1">
          {instLookUp[instrument_id].name} Requests
        </Typography>
      </AccordionSummary>
      <AccordionDetails
        data-testid={`${instLookUp[instrument_id].name}_observationplanRequestsTable`}
      >
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              data={requestsGroupedByInstId[instrument_id]}
              options={options}
              columns={getDataTableColumns(instrument_id)}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      </AccordionDetails>
    </Accordion>
  ));
};

ObservationPlanRequestLists.propTypes = {
  dateobs: PropTypes.string.isRequired,
};

export default ObservationPlanRequestLists;

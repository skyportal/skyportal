import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { makeStyles } from "tss-react/mui";
import { JSONTree } from "react-json-tree";

import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import * as Actions from "../../ducks/gcnEvent";
import AddSurveyEfficiencyObservationPlanPage from "../survey_efficiency/AddSurveyEfficiencyObservationPlanPage";
import AddRunFromObservationPlanPage from "./AddRunFromObservationPlanPage";
import ObservationPlanGlobe from "./ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "./ObservationPlanSummaryStatistics";
import { showNotification } from "baselayer/components/Notifications";

const useStyles = makeStyles()(() => ({
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
}));

const ObservationPlanRequestLists = ({ dateobs }) => {
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const [anchorEl, setAnchorEl] = useState(null);

  const observationPlanRequestList = gcnEvent?.observation_plans || [];
  const fetchedObservationPlan = gcnEvent?.observation_plan || null;

  const [
    observationPlanRequestFetchedForLocalization,
    setObservationPlanRequestFetchedForLocalization,
  ] = useState(null);

  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);

  const [showTable, setShowTable] = useState(null);

  useEffect(() => {
    if (!gcnEvent) return;
    if (
      selectedLocalizationId !== observationPlanRequestFetchedForLocalization
    ) {
      const fetchObservationPlanRequestList = async () => {
        setObservationPlanRequestFetchedForLocalization(selectedLocalizationId);
        dispatch(Actions.fetchObservationPlanRequests(gcnEvent.id));
      };
      fetchObservationPlanRequestList();
    }
  }, [
    dispatch,
    selectedLocalizationId,
    gcnEvent,
    observationPlanRequestFetchedForLocalization,
    dateobs,
  ]);

  function handleShowTable(id) {
    dispatch(Actions.fetchObservationPlan(id));
    setShowTable(id);
  }

  const [isDeleting, setIsDeleting] = useState(null);
  const handleDelete = async (id) => {
    setIsDeleting(id);
    await dispatch(Actions.deleteObservationPlanRequest(id));
    setIsDeleting(null);
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

  useEffect(() => {
    const getLocalizations = async () => {
      setSelectedLocalizationId(gcnEvent.localizations[0]?.id);
    };
    getLocalizations();
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
  }, [dispatch, setSelectedLocalizationId, gcnEvent]);

  if (
    !instrumentList ||
    !instrumentList.length ||
    !Object.keys(instrumentObsplanFormParams).length
  )
    return <CircularProgress />;

  if (!observationPlanRequestList?.length) {
    return <p>No observation plan requests for this event...</p>;
  }

  if (!gcnEvent.localizations.length || !selectedLocalizationId) {
    return <h3>Fetching skymap...</h3>;
  }

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const locLookUp = {};

  gcnEvent.localizations?.forEach((loc) => (locLookUp[loc.id] = loc));

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

    const renderManage = (params) => {
      const observationplanRequest = params.row;
      if (observationplanRequest.status === "running")
        return <CircularProgress />;

      const downloadLink = (rubinFormat = false) =>
        `/api/observation_plan/${
          observationplanRequest.id
        }?includePlannedObservations=True${
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
          observationplanRequest.id
        }.json`;
        link.click();
      };

      return (
        <div className={classes.actionButtons}>
          <Button
            secondary
            href={`/api/observation_plan/${observationplanRequest.id}/gcn`}
            download={`observation-plan-gcn-${observationplanRequest.id}`}
            size="small"
            data-testid={`gcnRequest_${observationplanRequest.id}`}
            disabled={!observationplanRequest.observation_plans?.length}
          >
            GCN
          </Button>
          <Button
            secondary
            size="small"
            onClick={(e) => setAnchorEl(e.currentTarget)}
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
              disabled={!observationplanRequest.observation_plans?.length}
            >
              Rubin compatible
            </MenuItem>
          </Menu>
          <Button
            secondary
            href={`/api/observation_plan/${observationplanRequest.id}/movie`}
            download={`observation-plan-movie-${observationplanRequest.id}`}
            size="small"
            disabled={!observationplanRequest.observation_plans?.length}
          >
            GIF
          </Button>
          <AddRunFromObservationPlanPage
            observationplanRequest={observationplanRequest}
          />
          <AddSurveyEfficiencyObservationPlanPage
            gcnevent={gcnEvent}
            observationplanRequest={observationplanRequest}
          />
          {implementsDelete && isDeleting === observationplanRequest.id ? (
            <CircularProgress />
          ) : (
            <Button
              primary
              onClick={() => handleDelete(observationplanRequest.id)}
              size="small"
              data-testid={`deleteRequest_${observationplanRequest.id}`}
              disabled={
                observationplanRequest.status === "submitted to telescope queue"
              }
              sx={{ marginBottom: "0.2rem" }}
            >
              Delete
            </Button>
          )}
        </div>
      );
    };

    const renderQueue = (params) => {
      const observationplanRequest = params.row;
      if (observationplanRequest.status === "running")
        return <CircularProgress />;
      if (
        observationplanRequest?.observation_plans?.length &&
        ["complete", "submitted to telescope queue"].includes(
          observationplanRequest?.observation_plans[0]?.status,
        ) &&
        observationplanRequest?.observation_plans[0]?.statistics?.length &&
        observationplanRequest?.observation_plans[0]?.statistics[0]?.statistics
          ?.num_observations === 0
      ) {
        return <div> No observations planned. </div>;
      }
      return (
        <div>
          {implementsSend && observationplanRequest.status === "complete" && (
            <Button
              primary
              onClick={() => handleShowTable(observationplanRequest.id)}
              size="small"
              disabled={isSending === observationplanRequest.id}
              sx={{ marginBottom: "0.2rem" }}
            >
              Send to Queue
            </Button>
          )}
          {implementsRemove &&
            observationplanRequest.status ===
              "submitted to telescope queue" && (
              <Button
                secondary
                onClick={() => handleRemove(observationplanRequest.id)}
                size="small"
                disabled={isRemoving === observationplanRequest.id}
                sx={{ marginBottom: "0.2rem" }}
              >
                Remove from Queue
              </Button>
            )}
          <Dialog
            open={showTable === observationplanRequest.id}
            onClose={() => setShowTable(null)}
            sx={{ minWidth: "60vw" }}
          >
            <DialogTitle>Observation plan</DialogTitle>
            <DialogContent>
              {fetchedObservationPlan &&
              fetchedObservationPlan.id === observationplanRequest.id ? (
                /* here will show a list (ordered by time) of all the observations in the plan */
                /* for each will show the time, field_id, filter */
                <>
                  <StyledDataGrid
                    autoHeight
                    rows={(
                      fetchedObservationPlan.observation_plans[0]
                        .planned_observations || []
                    ).map((row, i) => ({ ...row, __rowid: row.id ?? i }))}
                    getRowId={(row) => row.__rowid}
                    columns={[
                      {
                        field: "obstime",
                        headerName: "Time",
                        flex: 1,
                        minWidth: 160,
                      },
                      {
                        field: "field_id",
                        headerName: "Field ID",
                        flex: 1,
                        minWidth: 100,
                      },
                      {
                        field: "filt",
                        headerName: "Filter",
                        flex: 1,
                        minWidth: 90,
                      },
                      {
                        field: "exposure_time",
                        headerName: "Exposure Time",
                        flex: 1,
                        minWidth: 130,
                      },
                      {
                        field: "weight",
                        headerName: "Weight",
                        flex: 1,
                        minWidth: 90,
                      },
                    ]}
                    showToolbar
                  />
                  <Button
                    primary
                    onClick={() => handleSend(observationplanRequest.id)}
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

    const columns = [
      {
        field: "requester_username",
        headerName: "Requester",
        flex: 1,
        minWidth: 120,
        sortable: false,
        valueGetter: (value, row) => row.requester?.username,
      },
      {
        field: "allocation_group",
        headerName: "Allocation",
        flex: 1,
        minWidth: 120,
        sortable: false,
        valueGetter: (value, row) => row.allocation?.group?.name,
      },
      {
        field: "payload",
        headerName: "Payload",
        flex: 1,
        minWidth: 160,
        sortable: false,
        renderCell: (params) =>
          params.row ? (
            <div style={{ whiteSpace: "nowrap" }}>
              <JSONTree data={params.row.payload} hideRoot />
            </div>
          ) : null,
      },
      {
        field: "status",
        headerName: "Status",
        flex: 1,
        minWidth: 140,
        sortable: false,
        renderCell: (params) => (
          <Chip
            label={params.value}
            color={
              params.value === "complete"
                ? "success"
                : params.value === "submitted to telescope queue"
                  ? "warning"
                  : "default"
            }
          />
        ),
      },
      {
        field: "summarystatistics",
        headerName: "Summary Statistics",
        flex: 1,
        minWidth: 220,
        sortable: false,
        renderCell: (params) => {
          const observationplanRequest = params.row;
          if (observationplanRequest.status === "running")
            return <CircularProgress />;
          return (
            <Box sx={{ minWidth: "200px" }}>
              <ObservationPlanSummaryStatistics
                observationplanRequest={observationplanRequest}
              />
            </Box>
          );
        },
      },
      {
        field: "skymap",
        headerName: "Skymap",
        flex: 1,
        minWidth: 520,
        sortable: false,
        renderCell: (params) => {
          const observationplanRequest = params.row;
          if (
            !["complete", "running", "submitted to telescope queue"].includes(
              observationplanRequest?.status,
            )
          ) {
            return null;
          }
          return (
            <Box sx={{ minWidth: "500px" }}>
              <ObservationPlanGlobe
                observationplanRequest={observationplanRequest}
              />
            </Box>
          );
        },
      },
      {
        field: "manage",
        headerName: "Manage",
        flex: 1,
        minWidth: 240,
        sortable: false,
        filterable: false,
        renderCell: renderManage,
      },
    ];

    if (implementsSend || implementsRemove) {
      columns.push({
        field: "queue",
        headerName: "Telescope Queue",
        flex: 1,
        minWidth: 160,
        sortable: false,
        filterable: false,
        renderCell: renderQueue,
      });
    }

    columns.push({
      field: "treasuremap",
      headerName: "Treasure Map",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const observationplanRequest = params.row;
        if (observationplanRequest.status === "running")
          return <CircularProgress />;
        return (
          <div className={classes.actionButtons}>
            <Button
              secondary
              onClick={() => handleSubmitTreasureMap(observationplanRequest.id)}
              size="small"
              data-testid={`treasuremapRequest_${observationplanRequest.id}`}
              disabled={isSubmittingTreasureMap === observationplanRequest.id}
            >
              Send
            </Button>
            <Button
              sx={{ marginBottom: "0.2rem" }}
              secondary
              onClick={() => handleDeleteTreasureMap(observationplanRequest.id)}
              size="small"
              disabled={isDeletingTreasureMap === observationplanRequest.id}
            >
              Retract
            </Button>
          </div>
        );
      },
    });

    return columns;
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
        <StyledDataGrid
          autoHeight
          data-testid={`${instLookUp[instrument_id].name}_grid`}
          rows={requestsGroupedByInstId[instrument_id]}
          columns={getDataTableColumns(instrument_id)}
          getRowId={(row) => row.id}
          disableColumnFilter
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          pageSizeOptions={[1, 10, 15]}
          showToolbar
        />
      </AccordionDetails>
    </Accordion>
  ));
};

ObservationPlanRequestLists.propTypes = {
  dateobs: PropTypes.string.isRequired,
};

export default ObservationPlanRequestLists;

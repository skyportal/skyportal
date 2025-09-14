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
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";
import { JSONTree } from "react-json-tree";

import Button from "../Button";

import * as Actions from "../../ducks/gcnEvent";

import AddSurveyEfficiencyObservationPlanPage from "../survey_efficiency/AddSurveyEfficiencyObservationPlanPage";
import AddRunFromObservationPlanPage from "./AddRunFromObservationPlanPage";
import ObservationPlanGlobe from "./ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "./ObservationPlanSummaryStatistics";

const useStyles = makeStyles(() => ({
  observationplanRequestTable: {
    borderSpacing: "0.7em",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  accordion: {
    width: "99%",
  },
  container: {
    margin: "1rem 0",
  },
  localization: {
    minWidth: "500px",
  },
  summaryStatistics: {
    minWidth: "200px",
  },
  dialog: {
    minWidth: "60vw",
    "& .MuiDialog-paper": {
      minWidth: "60vw",
    },
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTable: {
        styleOverrides: {
          paper: {
            width: "100%",
          },
        },
      },
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
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
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

  const observationPlanRequestList = gcnEvent?.observation_plans || [];
  const fetchedObservationPlan = gcnEvent?.observation_plan || null;

  const [
    observationPlanRequestFetchedForLocalization,
    setObservationPlanRequestFetchedForLocalization,
  ] = useState(null);

  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);

  const [showTable, setShowTable] = useState(null);

  useEffect(() => {
    if (!gcnEvent) {
      return;
    }
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
    instrumentList.length === 0 ||
    Object.keys(instrumentObsplanFormParams).length === 0
  ) {
    return <CircularProgress />;
  }

  if (!observationPlanRequestList || observationPlanRequestList.length === 0) {
    return <p>No observation plan requests for this event...</p>;
  }

  if (gcnEvent.localizations.length === 0 || !selectedLocalizationId) {
    return <h3>Fetching skymap...</h3>;
  }

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const locLookUp = {};

  gcnEvent.localizations?.forEach((loc) => {
    locLookUp[loc.id] = loc;
  });

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

  Object.values(requestsGroupedByInstId).forEach((value) => {
    value.sort();
  });

  const getDataTableColumns = (instrument_id) => {
    const implementsDelete =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.delete;
    const implementsSend =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.send;
    const implementsRemove =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.remove;
    const queuable = implementsSend || implementsRemove;

    const columns = [
      { name: "requester.username", label: "Requester" },
      { name: "allocation.group.name", label: "Allocation" },
    ];
    const renderPayload = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];
      const cellStyle = {
        whiteSpace: "nowrap",
      };

      return (
        <div style={cellStyle}>
          {observationplanRequest ? (
            <JSONTree data={observationplanRequest.payload} hideRoot />
          ) : (
            ""
          )}
        </div>
      );
    };
    columns.push({
      name: "payload",
      label: "Payload",
      options: {
        customBodyRenderLite: renderPayload,
      },
    });

    columns.push({ name: "status", label: "Status" });

    const renderSummaryStatistics = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];

      return (
        <div>
          {observationplanRequest.status === "running" ? (
            <div>
              <CircularProgress />
            </div>
          ) : (
            <div className={classes.summaryStatistics}>
              <ObservationPlanSummaryStatistics
                observationplanRequest={observationplanRequest}
              />
            </div>
          )}
        </div>
      );
    };
    columns.push({
      name: "summarystatistics",
      label: "Summary Statistics",
      options: {
        customBodyRenderLite: renderSummaryStatistics,
      },
    });

    const renderLocalization = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];

      if (
        !["complete", "running", "submitted to telescope queue"].includes(
          observationplanRequest?.status,
        )
      ) {
        return <div />;
      }

      return (
        <div className={classes.localization}>
          <ObservationPlanGlobe
            observationplanRequest={observationplanRequest}
          />
        </div>
      );
    };
    columns.push({
      name: "skymap",
      label: "Skymap",
      options: {
        customBodyRenderLite: renderLocalization,
      },
    });

    const renderManage = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];

      const downloadLink = (rubinFormat = false) =>
        `/api/observation_plan/${
          observationplanRequest.id
        }?includePlannedObservations=True${
          rubinFormat ? "&rubinFormat=True" : ""
        }`;
      return (
        <div>
          {observationplanRequest.status === "running" ? (
            <div>
              <CircularProgress />
            </div>
          ) : (
            <div className={classes.actionButtons}>
              <div>
                <Button
                  secondary
                  href={`/api/observation_plan/${observationplanRequest.id}/gcn`}
                  download={`observation-plan-gcn-${observationplanRequest.id}`}
                  size="small"
                  type="submit"
                  data-testid={`gcnRequest_${observationplanRequest.id}`}
                  disabled={!observationplanRequest.observation_plans?.length}
                >
                  GCN
                </Button>
              </div>
              <div>
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
                    component="a"
                    href={downloadLink()}
                    download={`observation-plan-${observationplanRequest.id}`}
                    onClick={() => setAnchorEl(null)}
                  >
                    ZTF compatible
                  </MenuItem>
                  <MenuItem
                    component="a"
                    href={downloadLink(true)}
                    download={`rubin-observation-plan-${observationplanRequest.id}`}
                    onClick={() => setAnchorEl(null)}
                    disabled={!observationplanRequest.observation_plans?.length}
                  >
                    Rubin compatible
                  </MenuItem>
                </Menu>
              </div>
              <div>
                <Button
                  secondary
                  href={`/api/observation_plan/${observationplanRequest.id}/movie`}
                  download={`observation-plan-movie-${observationplanRequest.id}`}
                  size="small"
                  type="submit"
                  data-testid={`movieRequest_${observationplanRequest.id}`}
                  disabled={!observationplanRequest.observation_plans?.length}
                >
                  GIF
                </Button>
              </div>
              <div>
                <AddRunFromObservationPlanPage
                  observationplanRequest={observationplanRequest}
                />
              </div>
              <div>
                <AddSurveyEfficiencyObservationPlanPage
                  gcnevent={gcnEvent}
                  observationplanRequest={observationplanRequest}
                />
              </div>
              <div className={classes.actionButtons}>
                {implementsDelete &&
                isDeleting === observationplanRequest.id ? (
                  <div>
                    <CircularProgress />
                  </div>
                ) : (
                  <div>
                    <Button
                      primary
                      onClick={() => {
                        handleDelete(observationplanRequest.id);
                      }}
                      size="small"
                      type="submit"
                      data-testid={`deleteRequest_${observationplanRequest.id}`}
                      disabled={
                        observationplanRequest.status ===
                        "submitted to telescope queue"
                      }
                    >
                      Delete
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      );
    };

    columns.push({
      name: "manage",
      label: "Manage",
      options: {
        customBodyRenderLite: renderManage,
      },
    });

    if (queuable) {
      const renderQueue = (dataIndex) => {
        const observationplanRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];
        if (observationplanRequest.status === "running") {
          return (
            <div>
              <CircularProgress />
            </div>
          );
        }
        if (
          observationplanRequest?.observation_plans?.length > 0 &&
          ["complete", "submitted to telescope queue"].includes(
            observationplanRequest?.observation_plans[0]?.status,
          ) &&
          observationplanRequest?.observation_plans[0]?.statistics?.length >
            0 &&
          observationplanRequest?.observation_plans[0]?.statistics[0]
            ?.statistics?.num_observations === 0
        ) {
          return <div> No observations planned. </div>;
        }
        return (
          <div>
            <div className={classes.actionButtons}>
              {implementsSend && isSending === observationplanRequest.id ? (
                <div>
                  <CircularProgress />
                </div>
              ) : (
                <div
                  style={{
                    display:
                      observationplanRequest.status === "complete"
                        ? "block"
                        : "none",
                  }}
                >
                  <Button
                    primary
                    onClick={() => {
                      handleShowTable(observationplanRequest.id);
                    }}
                    size="small"
                    type="submit"
                    data-testid={`sendRequest_${observationplanRequest.id}`}
                  >
                    Send to Queue
                  </Button>
                </div>
              )}
              {implementsRemove && isRemoving === observationplanRequest.id ? (
                <div>
                  <CircularProgress />
                </div>
              ) : (
                <div
                  style={{
                    display:
                      observationplanRequest.status ===
                      "submitted to telescope queue"
                        ? "block"
                        : "none",
                  }}
                >
                  <Button
                    secondary
                    onClick={() => {
                      handleRemove(observationplanRequest.id);
                    }}
                    size="small"
                    type="submit"
                    data-testid={`removeRequest_${observationplanRequest.id}`}
                  >
                    Remove from Queue
                  </Button>
                </div>
              )}
            </div>
            <Dialog
              open={showTable === observationplanRequest.id}
              onClose={() => {
                setShowTable(null);
              }}
              className={classes.dialog}
            >
              <DialogTitle>Observation plan</DialogTitle>
              <DialogContent>
                {fetchedObservationPlan &&
                fetchedObservationPlan.id === observationplanRequest.id ? (
                  /* here will show a list (ordered by time) of all the observations in the plan */
                  /* for each will show the time, field_id, filter */
                  <>
                    <MUIDataTable
                      data={
                        fetchedObservationPlan.observation_plans[0]
                          .planned_observations
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
                      onClick={() => {
                        handleSend(observationplanRequest.id);
                      }}
                      size="small"
                      type="submit"
                      data-testid={`sendRequest_${observationplanRequest.id}`}
                    >
                      Send to Queue
                    </Button>
                  </>
                ) : (
                  <div>
                    <CircularProgress />
                  </div>
                )}
              </DialogContent>
            </Dialog>
          </div>
        );
      };
      columns.push({
        name: "queue",
        label: "Telescope Queue",
        options: {
          customBodyRenderLite: renderQueue,
        },
      });
    }

    const renderTreasureMap = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {observationplanRequest.status === "running" ? (
            <div>
              <CircularProgress />
            </div>
          ) : (
            <div className={classes.actionButtons}>
              {isSubmittingTreasureMap === observationplanRequest.id ? (
                <div>
                  <CircularProgress />
                </div>
              ) : (
                <div>
                  <Button
                    secondary
                    onClick={() => {
                      handleSubmitTreasureMap(observationplanRequest.id);
                    }}
                    size="small"
                    type="submit"
                    data-testid={`treasuremapRequest_${observationplanRequest.id}`}
                  >
                    Send
                  </Button>
                </div>
              )}
              {isDeletingTreasureMap === observationplanRequest.id ? (
                <div>
                  <CircularProgress />
                </div>
              ) : (
                <div>
                  <Button
                    secondary
                    onClick={() => {
                      handleDeleteTreasureMap(observationplanRequest.id);
                    }}
                    size="small"
                    type="submit"
                    data-testid={`treasuremapDelete_${observationplanRequest.id}`}
                  >
                    Retract
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      );
    };
    columns.push({
      name: "treasuremap",
      label: "Treasure Map",
      options: {
        customBodyRenderLite: renderTreasureMap,
      },
    });

    return columns;
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

  return (
    <div className={classes.container}>
      {Object.keys(requestsGroupedByInstId).map((instrument_id) => (
        // get the flat, unique list of all keys across all requests
        <Accordion
          className={classes.accordion}
          key={`instrument_${instrument_id}_table_div`}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls={`${instLookUp[instrument_id].name}-requests`}
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
      ))}
    </div>
  );
};

ObservationPlanRequestLists.propTypes = {
  dateobs: PropTypes.string.isRequired,
};

export default ObservationPlanRequestLists;

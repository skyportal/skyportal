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
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";
import Button from "./Button";

import * as Actions from "../ducks/gcnEvent";
import { GET } from "../API";

import LocalizationPlot from "./LocalizationPlot";
import AddSurveyEfficiencyObservationPlanPage from "./AddSurveyEfficiencyObservationPlanPage";
import AddRunFromObservationPlanPage from "./AddRunFromObservationPlanPage";

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
    minWidth: "250px",
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
    overrides: {
      MUIDataTable: {
        paper: {
          width: "100%",
        },
      },
      MUIDataTableBodyCell: {
        stackedCommon: {
          overflow: "hidden",
          "&:last-child": {
            paddingLeft: "0.25rem",
          },
        },
      },
      MUIDataTablePagination: {
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
  });

const ObservationPlanGlobe = ({ observationplanRequest }) => {
  const dispatch = useDispatch();

  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault = Object.fromEntries(
    displayOptions.map((x) => [x, false]),
  );
  displayOptionsDefault.localization = true;
  displayOptionsDefault.observations = true;

  const [obsList, setObsList] = useState(null);
  useEffect(() => {
    const fetchObsList = async () => {
      const response = await dispatch(
        GET(
          `/api/observation_plan/${observationplanRequest.id}/geojson`,
          "skyportal/FETCH_OBSERVATION_PLAN_GEOJSON",
        ),
      );
      setObsList(response.data);
    };
    if (
      ["complete", "submitted to telescope queue"].includes(
        observationplanRequest?.status,
      )
    ) {
      fetchObsList();
    }
  }, [dispatch, setObsList, observationplanRequest]);

  const handleDeleteObservationPlanFields = async (obsPlanList) => {
    const selectedFields = obsPlanList?.geojson.filter((f) => f?.selected);
    const selectedIds = selectedFields.map((f) => f?.properties?.field_id);
    await dispatch(
      Actions.deleteObservationPlanFields(
        observationplanRequest.id,
        selectedIds,
      ),
    );
  };

  return (
    <div>
      {!obsList ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <LocalizationPlot
            observations={obsList}
            options={displayOptionsDefault}
            height={550}
            width={550}
            type="obsplan"
            projection="mollweide"
          />
          <Button
            secondary
            onClick={() => handleDeleteObservationPlanFields(obsList)}
          >
            Delete selected fields
          </Button>
        </div>
      )}
    </div>
  );
};

ObservationPlanGlobe.propTypes = {
  observationplanRequest: PropTypes.shape({
    id: PropTypes.number,
    requester: PropTypes.shape({
      id: PropTypes.number,
      username: PropTypes.string,
    }),
    instrument: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
    status: PropTypes.string,
    allocation: PropTypes.shape({
      group: PropTypes.shape({
        name: PropTypes.string,
      }),
    }),
  }).isRequired,
};

const ObservationPlanSummaryStatistics = ({ observationplanRequest }) => {
  const summaryStatistics =
    observationplanRequest?.observation_plans[0]?.statistics;

  return (
    <div>
      {!summaryStatistics || summaryStatistics?.length === 0 ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <ul>
            <li>
              {" "}
              Number of Observations:{" "}
              {summaryStatistics[0].statistics.num_observations}{" "}
            </li>
            <li> Delay from Trigger: {summaryStatistics[0].statistics.dt} </li>
            <li>
              {" "}
              Start of Observations:{" "}
              {summaryStatistics[0].statistics.start_observation}{" "}
            </li>
            <li>
              {" "}
              Unique filters:{" "}
              {summaryStatistics[0].statistics.unique_filters?.join(", ")}{" "}
            </li>
            <li>
              {" "}
              Total time [s]: {summaryStatistics[0].statistics.total_time}{" "}
            </li>
            <li>
              {" "}
              Probability:{" "}
              {summaryStatistics[0].statistics.probability?.toFixed(3)}{" "}
            </li>
            <li>
              {" "}
              Area [sq. deg.]:{" "}
              {summaryStatistics[0].statistics.area?.toFixed(1)}{" "}
            </li>
          </ul>
        </div>
      )}
    </div>
  );
};

ObservationPlanSummaryStatistics.propTypes = {
  observationplanRequest: PropTypes.shape({
    id: PropTypes.number,
    requester: PropTypes.shape({
      id: PropTypes.number,
      username: PropTypes.string,
    }),
    instrument: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
    }),
    status: PropTypes.string,
    allocation: PropTypes.shape({
      group: PropTypes.shape({
        name: PropTypes.string,
      }),
    }),
    observation_plans: PropTypes.arrayOf(
      PropTypes.shape({
        statistics: PropTypes.arrayOf(
          PropTypes.shape({
            statistics: PropTypes.shape({
              id: PropTypes.number,
              probability: PropTypes.number,
              area: PropTypes.number,
              num_observations: PropTypes.number,
              dt: PropTypes.number,
              total_time: PropTypes.number,
              start_observation: PropTypes.string,
              unique_filters: PropTypes.arrayOf(PropTypes.string),
            }),
          }),
        ),
      }),
    ),
  }).isRequired,
};

const ObservationPlanRequestLists = ({ dateobs }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();

  const gcnEvent = useSelector((state) => state.gcnEvent);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  // eslint-disable-next-line no-unused-expressions
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

  const getDataTableColumns = (keys, instrument_id) => {
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
    keys?.forEach((key) => {
      const renderKey = (value) =>
        Array.isArray(value) ? value.join(",") : value;

      if (instrumentObsplanFormParams[instrument_id]) {
        const field = Object.keys(
          instrumentObsplanFormParams[instrument_id].aliasLookup,
        ).includes(key)
          ? instrumentObsplanFormParams[instrument_id].aliasLookup[key]
          : key;
        columns.push({
          name: `payload.${key}`,
          label: field,
          options: {
            customBodyRender: renderKey,
          },
        });
      }
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
            <div>
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

    const renderDelete = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];

      return (
        <div>
          <div className={classes.actionButtons}>
            {implementsDelete && isDeleting === observationplanRequest.id ? (
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
                >
                  Delete
                </Button>
              </div>
            )}
          </div>
        </div>
      );
    };
    columns.push({
      name: "delete",
      label: "Delete",
      options: {
        customBodyRenderLite: renderDelete,
      },
    });

    const renderModify = (dataIndex) => {
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
              <div>
                <Button
                  secondary
                  href={`/api/observation_plan/${observationplanRequest.id}/gcn`}
                  download={`observation-plan-gcn-${observationplanRequest.id}`}
                  size="small"
                  type="submit"
                  data-testid={`gcnRequest_${observationplanRequest.id}`}
                >
                  GCN
                </Button>
              </div>
              <div>
                <Button
                  secondary
                  href={`/api/observation_plan/${observationplanRequest.id}?includePlannedObservations=True`}
                  download={`observation-plan-${observationplanRequest.id}`}
                  size="small"
                  type="submit"
                  data-testid={`downloadRequest_${observationplanRequest.id}`}
                >
                  Download
                </Button>
              </div>
              <div>
                <Button
                  secondary
                  href={`/api/observation_plan/${observationplanRequest.id}/movie`}
                  download={`observation-plan-movie-${observationplanRequest.id}`}
                  size="small"
                  type="submit"
                  data-testid={`movieRequest_${observationplanRequest.id}`}
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
            </div>
          )}
        </div>
      );
    };
    columns.push({
      name: "interact",
      label: "Interact",
      options: {
        customBodyRenderLite: renderModify,
      },
    });

    if (queuable) {
      const renderQueue = (dataIndex) => {
        const observationplanRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];
        return (
          <div>
            {observationplanRequest.status === "running" ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <>
                <div className={classes.actionButtons}>
                  {implementsSend && isSending === observationplanRequest.id ? (
                    <div>
                      <CircularProgress />
                    </div>
                  ) : (
                    <div>
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
                  {implementsRemove &&
                  isRemoving === observationplanRequest.id ? (
                    <div>
                      <CircularProgress />
                    </div>
                  ) : (
                    <div>
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
                  style={{ position: "fixed" }}
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
              </>
            )}
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
                    Send to Treasure Map
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
                    Retract from Treasure Map
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

    const renderLocalization = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];

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

  const keyOrder = (a, b) => {
    // End date comes after start date
    if (a === "end_date" && b === "start_date") {
      return 1;
    }
    if (b === "end_date" && a === "start_date") {
      return -1;
    }

    // Dates come before anything else
    if (a === "end_date" || a === "start_date") {
      return -1;
    }
    if (b === "end_date" || b === "start_date") {
      return 1;
    }

    // Regular string comparison
    if (a < b) {
      return -1;
    }
    if (a > b) {
      return 1;
    }
    // a must be equal to b
    return 0;
  };

  return (
    <div className={classes.container}>
      {Object.keys(requestsGroupedByInstId).map((instrument_id) => {
        // get the flat, unique list of all keys across all requests
        const keys = requestsGroupedByInstId[instrument_id].reduce((r, a) => {
          Object.keys(a.payload).forEach((key) => {
            if (!r.includes(key)) {
              r = [...r, key];
            }
          });
          return r;
        }, []);

        keys.sort(keyOrder);

        return (
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
                    columns={getDataTableColumns(keys, instrument_id)}
                  />
                </ThemeProvider>
              </StyledEngineProvider>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </div>
  );
};

ObservationPlanRequestLists.propTypes = {
  dateobs: PropTypes.string.isRequired,
};

export default ObservationPlanRequestLists;

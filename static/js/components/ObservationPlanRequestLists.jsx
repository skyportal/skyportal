import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Button from "@material-ui/core/Button";
import CircularProgress from "@material-ui/core/CircularProgress";
import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import Typography from "@material-ui/core/Typography";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import {
  makeStyles,
  createTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import MUIDataTable from "mui-datatables";

import * as Actions from "../ducks/gcnEvent";
import { GET } from "../API";

import LocalizationPlot from "./LocalizationPlot";

const useStyles = makeStyles(() => ({
  observationplanRequestTable: {
    borderSpacing: "0.7em",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
  },
  accordion: {
    width: "99%",
  },
  container: {
    margin: "1rem 0",
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

const ObservationPlanGlobe = ({ observationplanRequest, loc }) => {
  const dispatch = useDispatch();

  const displayOptions = [
    "localization",
    "sources",
    "galaxies",
    "instrument",
    "observations",
  ];
  const displayOptionsDefault = Object.fromEntries(
    displayOptions.map((x) => [x, false])
  );
  displayOptionsDefault.localization = true;
  displayOptionsDefault.observations = true;

  const [obsList, setObsList] = useState(null);
  useEffect(() => {
    const fetchObsList = async () => {
      const response = await dispatch(
        GET(
          `/api/observation_plan/${observationplanRequest.id}/geojson`,
          "skyportal/FETCH_OBSERVATION_PLAN_GEOJSON"
        )
      );
      setObsList(response.data);
    };
    fetchObsList();
    if (obsList && Array.isArray(obsList)) {
      obsList.forEach((f) => {
        f.selected = false;
      });
    }
  }, [dispatch, setObsList, observationplanRequest]);

  return (
    <div>
      {!obsList ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <LocalizationPlot
            loc={loc}
            observations={obsList}
            options={displayOptionsDefault}
            height={300}
            width={300}
          />
        </div>
      )}
    </div>
  );
};

ObservationPlanGlobe.propTypes = {
  loc: PropTypes.shape({
    id: PropTypes.number,
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
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

const ObservationPlanRequestLists = ({ gcnEvent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();

  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);

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
  };

  const [isRemoving, setIsRemoving] = useState(null);
  const handleRemove = async (id) => {
    setIsRemoving(id);
    await dispatch(Actions.removeObservationPlanRequest(id));
    setIsRemoving(null);
  };

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
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
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <CircularProgress />;
  }

  if (
    !gcnEvent.observationplan_requests ||
    gcnEvent.observationplan_requests.length === 0
  ) {
    return <p>No observation plan requests for this source...</p>;
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

  const requestsGroupedByInstId = gcnEvent.observationplan_requests.reduce(
    (r, a) => {
      r[a.allocation.instrument.id] = [
        ...(r[a.allocation.instrument.id] || []),
        a,
      ];
      return r;
    },
    {}
  );

  Object.values(requestsGroupedByInstId).forEach((value) => {
    value.sort();
  });

  const getDataTableColumns = (keys, instrument_id) => {
    const implementsDelete =
      instrumentFormParams[instrument_id]?.methodsImplemented.delete;
    const implementsSend =
      instrumentFormParams[instrument_id]?.methodsImplemented.send;
    const implementsRemove =
      instrumentFormParams[instrument_id]?.methodsImplemented.remove;
    const modifiable = implementsDelete;
    const queuable = implementsSend || implementsRemove;

    const columns = [
      { name: "requester.username", label: "Requester" },
      { name: "allocation.group.name", label: "Allocation" },
    ];
    keys?.forEach((key) => {
      const renderKey = (value) =>
        Array.isArray(value) ? value.join(",") : value;

      if (instrumentFormParams[instrument_id]) {
        const field = Object.keys(
          instrumentFormParams[instrument_id].aliasLookup
        ).includes(key)
          ? instrumentFormParams[instrument_id].aliasLookup[key]
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

    const renderNumberObservations = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {observationplanRequest.observation_plans &&
          observationplanRequest.observation_plans.length > 0 ? (
            <div>
              {observationplanRequest.observation_plans[0].num_observations}
            </div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "nobs",
      label: "Number of Observations",
      options: {
        customBodyRenderLite: renderNumberObservations,
      },
    });

    const renderArea = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {observationplanRequest.observation_plans &&
          observationplanRequest.observation_plans.length > 0 ? (
            <div>
              {observationplanRequest.observation_plans[0].area.toFixed(2)}
            </div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "area",
      label: "Area [sq. deg.]",
      options: {
        customBodyRenderLite: renderArea,
      },
    });

    const renderProbability = (dataIndex) => {
      const observationplanRequest =
        requestsGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          {observationplanRequest.observation_plans &&
          observationplanRequest.observation_plans.length > 0 ? (
            <div>
              {observationplanRequest.observation_plans[0].probability.toFixed(
                3
              )}
            </div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      );
    };
    columns.push({
      name: "probability",
      label: "Int. Probability",
      options: {
        customBodyRenderLite: renderProbability,
      },
    });

    if (modifiable) {
      const renderModify = (dataIndex) => {
        const observationplanRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];
        return (
          <div className={classes.actionButtons}>
            {implementsDelete && isDeleting === observationplanRequest.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  onClick={() => {
                    handleDelete(observationplanRequest.id);
                  }}
                  size="small"
                  color="primary"
                  type="submit"
                  variant="outlined"
                  data-testid={`deleteRequest_${observationplanRequest.id}`}
                >
                  Delete
                </Button>
              </div>
            )}
            <div>
              <Button
                href={`/api/observation_plan/${observationplanRequest.id}/gcn`}
                download={`observation-plan-gcn-${observationplanRequest.id}`}
                size="small"
                color="primary"
                type="submit"
                variant="outlined"
                data-testid={`gcnRequest_${observationplanRequest.id}`}
              >
                GCN
              </Button>
            </div>
            <div>
              <Button
                href={`/api/observation_plan/${observationplanRequest.id}?includePlannedObservations=True`}
                download={`observation-plan-${observationplanRequest.id}`}
                size="small"
                color="primary"
                type="submit"
                variant="outlined"
                data-testid={`downloadRequest_${observationplanRequest.id}`}
              >
                Download
              </Button>
            </div>
            <div>
              <Button
                href={`/api/observation_plan/${observationplanRequest.id}/movie`}
                download={`observation-plan-movie-${observationplanRequest.id}`}
                size="small"
                color="primary"
                type="submit"
                variant="outlined"
                data-testid={`movieRequest_${observationplanRequest.id}`}
              >
                GIF
              </Button>
            </div>
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
    }

    if (queuable) {
      const renderQueue = (dataIndex) => {
        const observationplanRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];
        return (
          <div className={classes.actionButtons}>
            {implementsSend && isSending === observationplanRequest.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  onClick={() => {
                    handleSend(observationplanRequest.id);
                  }}
                  size="small"
                  color="primary"
                  type="submit"
                  variant="outlined"
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
              <div>
                <Button
                  onClick={() => {
                    handleRemove(observationplanRequest.id);
                  }}
                  size="small"
                  color="primary"
                  type="submit"
                  variant="outlined"
                  data-testid={`removeRequest_${observationplanRequest.id}`}
                >
                  Remove from Queue
                </Button>
              </div>
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
        <div className={classes.actionButtons}>
          {isSubmittingTreasureMap === observationplanRequest.id ? (
            <div>
              <CircularProgress />
            </div>
          ) : (
            <div>
              <Button
                onClick={() => {
                  handleSubmitTreasureMap(observationplanRequest.id);
                }}
                size="small"
                color="primary"
                type="submit"
                variant="outlined"
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
                onClick={() => {
                  handleDeleteTreasureMap(observationplanRequest.id);
                }}
                size="small"
                color="primary"
                type="submit"
                variant="outlined"
                data-testid={`treasuremapDelete_${observationplanRequest.id}`}
              >
                Retract from Treasure Map
              </Button>
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
        <div>
          <ObservationPlanGlobe
            loc={locLookUp[selectedLocalizationId]}
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
              <MuiThemeProvider theme={getMuiTheme(theme)}>
                <MUIDataTable
                  data={requestsGroupedByInstId[instrument_id]}
                  options={options}
                  columns={getDataTableColumns(keys, instrument_id)}
                />
              </MuiThemeProvider>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </div>
  );
};

ObservationPlanRequestLists.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
    observationplan_requests: PropTypes.arrayOf(
      PropTypes.shape({
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
      })
    ),
  }).isRequired,
};

export default ObservationPlanRequestLists;

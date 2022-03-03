import React, { useState } from "react";
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

const ObservationPlanRequestLists = ({ observationplanRequests }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();

  const [isDeleting, setIsDeleting] = useState(null);
  const handleDelete = async (id) => {
    setIsDeleting(id);
    await dispatch(Actions.deleteObservationPlanRequest(id));
    setIsDeleting(null);
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

  if (
    !instrumentList ||
    instrumentList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <CircularProgress />;
  }

  if (!observationplanRequests || observationplanRequests.length === 0) {
    return <p>No observation plan requests for this source...</p>;
  }

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const requestsGroupedByInstId = observationplanRequests.reduce((r, a) => {
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
      instrumentFormParams[instrument_id].methodsImplemented.delete;
    const implementsSend =
      instrumentFormParams[instrument_id].methodsImplemented.send;
    const implementsRemove =
      instrumentFormParams[instrument_id].methodsImplemented.remove;
    const modifiable = implementsDelete;
    const queuable = implementsSend || implementsRemove;

    const columns = [
      { name: "requester.username", label: "Requester" },
      { name: "allocation.group.name", label: "Allocation" },
    ];
    keys?.forEach((key) => {
      const renderKey = (value) =>
        Array.isArray(value) ? value.join(",") : value;

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
    });
    columns.push({ name: "status", label: "Status" });
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
        name: "queue",
        label: "Telescope Queue",
        options: {
          customBodyRenderLite: renderQueue,
        },
      });
    }

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
  observationplanRequests: PropTypes.arrayOf(
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
  ).isRequired,
};

export default ObservationPlanRequestLists;

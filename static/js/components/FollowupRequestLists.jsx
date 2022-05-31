import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
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

import * as Actions from "../ducks/source";

import EditFollowupRequestDialog from "./EditFollowupRequestDialog";

const useStyles = makeStyles(() => ({
  followupRequestTable: {
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

const FollowupRequestLists = ({
  followupRequests,
  instrumentList,
  instrumentFormParams,
  totalMatches,
  handleTableChange = false,
  pageNumber = 1,
  numPerPage = 10,
  showObject = false,
  serverSide = false,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();

  const [isDeleting, setIsDeleting] = useState(null);
  const handleDelete = async (id) => {
    setIsDeleting(id);
    await dispatch(Actions.deleteFollowupRequest(id));
    setIsDeleting(null);
  };

  const [isGetting, setIsGetting] = useState(null);
  const handleGet = async (id) => {
    setIsGetting(id);
    await dispatch(Actions.getPhotometryRequest(id));
    setIsGetting(null);
  };

  if (
    instrumentList.length === 0 ||
    followupRequests.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>No robotic followup requests found...</p>;
  }

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  if (!Array.isArray(followupRequests)) {
    return <p>Waiting for followup requests to load...</p>;
  }

  const requestsGroupedByInstId = followupRequests.reduce((r, a) => {
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
    const columns = [
      { name: "requester.username", label: "Requester" },
      { name: "allocation.group.name", label: "Allocation" },
    ];

    if (!(instrument_id in instrumentFormParams)) {
      return columns;
    }
    const implementsDelete =
      instrumentFormParams[instrument_id].methodsImplemented.delete;
    const implementsEdit =
      instrumentFormParams[instrument_id].methodsImplemented.update;
    const implementsGet =
      instrumentFormParams[instrument_id].methodsImplemented.get;
    const modifiable = implementsEdit || implementsDelete || implementsGet;

    if (showObject) {
      const renderObj = (dataIndex) => {
        const followupRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];
        return (
          <div>
            {followupRequest.obj ? (
              <Button
                size="small"
                data-testid={`link_${followupRequest.obj.id}`}
              >
                <a href={`/source/${followupRequest.obj.id}`}>
                  {followupRequest.obj.id}&nbsp;
                </a>
              </Button>
            ) : (
              <CircularProgress />
            )}
          </div>
        );
      };
      columns.push({
        name: "obj",
        label: "Object",
        options: {
          sort: true,
          sortThirdClickReset: true,
          customBodyRenderLite: renderObj,
        },
      });
    }

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
        const followupRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];
        return (
          <div className={classes.actionButtons}>
            {implementsDelete && isDeleting === followupRequest.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  onClick={() => {
                    handleDelete(followupRequest.id);
                  }}
                  size="small"
                  color="primary"
                  type="submit"
                  variant="outlined"
                  data-testid={`deleteRequest_${followupRequest.id}`}
                >
                  Delete
                </Button>
              </div>
            )}
            {implementsGet && isGetting === followupRequest.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  onClick={() => {
                    handleGet(followupRequest.id);
                  }}
                  size="small"
                  color="primary"
                  type="submit"
                  variant="outlined"
                  data-testid={`getRequest_${followupRequest.id}`}
                >
                  Retrieve
                </Button>
              </div>
            )}
            {implementsEdit && (
              <EditFollowupRequestDialog
                followupRequest={followupRequest}
                instrumentFormParams={instrumentFormParams}
              />
            )}
          </div>
        );
      };
      columns.push({
        name: "modify",
        label: "Modify",
        options: {
          customBodyRenderLite: renderModify,
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
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [10, 25, 50, 100],
    jumpToPage: true,
    serverSide,
    pagination: true,
    count: totalMatches,
  };
  if (typeof handleTableChange === "function") {
    options.onTableChange = handleTableChange;
  }

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
              data-testid={`${instLookUp[instrument_id].name}_followupRequestsTable`}
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

FollowupRequestLists.propTypes = {
  followupRequests: PropTypes.arrayOf(
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
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      band: PropTypes.string,
      created_at: PropTypes.string,
      id: PropTypes.number,
      name: PropTypes.string,
      type: PropTypes.string,
      telescope_id: PropTypes.number,
    })
  ).isRequired,
  instrumentFormParams: PropTypes.shape({
    // eslint-disable-next-line react/forbid-prop-types
    formSchema: PropTypes.objectOf(PropTypes.any),
    // eslint-disable-next-line react/forbid-prop-types
    uiSchema: PropTypes.objectOf(PropTypes.any),
    // eslint-disable-next-line react/forbid-prop-types
    methodsImplemented: PropTypes.objectOf(PropTypes.any),
    // eslint-disable-next-line react/forbid-prop-types
    aliasLookup: PropTypes.objectOf(PropTypes.any),
  }).isRequired,
  handleTableChange: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  showObject: PropTypes.bool,
  serverSide: PropTypes.bool,
};

FollowupRequestLists.defaultProps = {
  showObject: false,
  serverSide: false,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};
export default FollowupRequestLists;

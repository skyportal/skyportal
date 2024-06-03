import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import WatcherButton from "../WatcherButton";

import * as Actions from "../../ducks/source";

import EditFollowupRequestDialog from "../EditFollowupRequestDialog";

const useStyles = makeStyles(() => ({
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
  },
  accordion: {
    width: "100%",
  },
  container: {
    margin: "0 1px 1px 1px",
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

const displayedColumns = [
  "requester",
  "allocation",
  "start_date",
  "end_date",
  "mode",
  "request",
  "filter",
  "filters",
  "field_ids",
  "priority",
  "status",
  "modify",
  "watch",
];

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
  requestType = "triggered",
  onDownload = false,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const theme = useTheme();

  const [isDeleting, setIsDeleting] = useState(null);
  const handleDelete = async (id) => {
    setIsDeleting(id);
    const params = {};
    if (serverSide) {
      params.refreshRequests = true;
    }
    await dispatch(Actions.deleteFollowupRequest(id, params));
    setIsDeleting(null);
  };

  const [isGetting, setIsGetting] = useState(null);
  const [hasRetrieved, setHasRetrieved] = useState([]);
  const handleGet = async (id) => {
    setIsGetting(id);
    const params = {};
    if (serverSide) {
      params.refreshRequests = true;
    }
    dispatch(Actions.getPhotometryRequest(id, params)).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification(
            "Successfully retrieved photometry request, please wait for it to be processed.",
            "success",
          ),
        );
        setHasRetrieved([...hasRetrieved, id]);
      }
      setIsGetting(null);
    });
  };

  const [isSubmitting, setIsSubmitting] = useState(null);
  const handleSubmit = async (followupRequest) => {
    setIsSubmitting(followupRequest.id);
    const json = {
      allocation_id: followupRequest.allocation.id,
      obj_id: followupRequest.obj_id,
      payload: followupRequest.payload,
    };
    if (serverSide) {
      json.refreshRequests = true;
    }
    await dispatch(Actions.editFollowupRequest(json, followupRequest.id));
    setIsSubmitting(null);
  };

  if (requestType === "triggered") {
    instrumentList = instrumentList.filter(
      // find the instrument in instrumentFormParams that has the same id as the instrument in instrumentList
      (inst) =>
        inst.id in instrumentFormParams &&
        instrumentFormParams[inst.id]?.formSchema !== null &&
        instrumentFormParams[inst.id]?.formSchema !== undefined,
    );

    followupRequests = followupRequests.filter(
      (request) =>
        request?.payload?.request_type === "triggered" ||
        (request?.allocation?.instrument_id in instrumentFormParams &&
          (instrumentFormParams[request?.allocation?.instrument_id]
            ?.formSchemaForcedPhotometry === null ||
            instrumentFormParams[request?.allocation?.instrument_id]
              ?.formSchemaForcedPhotometry === undefined)),
    );
  } else if (requestType === "forced_photometry") {
    instrumentList = instrumentList.filter(
      // find the instrument in instrumentFormParams that has the same id as the instrument in instrumentList
      (inst) =>
        inst.id in instrumentFormParams &&
        instrumentFormParams[inst.id]?.formSchemaForcedPhotometry !== null &&
        instrumentFormParams[inst.id]?.formSchemaForcedPhotometry !== undefined,
    );

    followupRequests = followupRequests.filter(
      (request) =>
        request?.payload?.request_type === "forced_photometry" ||
        (request?.allocation?.instrument_id in instrumentFormParams &&
          (instrumentFormParams[request?.allocation?.instrument_id]
            ?.formSchema === null ||
            instrumentFormParams[request?.allocation?.instrument_id]
              ?.formSchema === undefined)),
    );
  }

  if (
    (instrumentList.length === 0 ||
      followupRequests.length === 0 ||
      Object.keys(instrumentFormParams).length === 0) &&
    !serverSide
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

  const getDataTableColumns = (keys, instrument_id) => {
    const columns = [
      { name: "requester.username", label: "Requester" },
      { name: "allocation.group.name", label: "Group" },
      { name: "allocation.pi", label: "PI" },
    ];

    if (!(instrument_id in instrumentFormParams)) {
      return columns;
    }
    const implementSubmit =
      instrumentFormParams[instrument_id].methodsImplemented.submit;
    const implementsDelete =
      instrumentFormParams[instrument_id].methodsImplemented.delete;
    const implementsEdit =
      instrumentFormParams[instrument_id].methodsImplemented.update &&
      requestType === "triggered";
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
        instrumentFormParams[instrument_id].aliasLookup,
      ).includes(key)
        ? instrumentFormParams[instrument_id].aliasLookup[key]
        : key;
      columns.push({
        name: `payload.${key}`,
        label: field,
        options: {
          customBodyRender: renderKey,
          display: displayedColumns.includes(field.toLowerCase()),
        },
      });
    });
    columns.push({ name: "status", label: "Status" });
    if (modifiable) {
      const renderModify = (dataIndex) => {
        const followupRequest =
          requestsGroupedByInstId[instrument_id][dataIndex];

        const isDone =
          followupRequest.status === "Photometry committed to database";

        const isSubmitted = followupRequest.status === "submitted";

        const isFailed = followupRequest.status === "failed to submit";

        return (
          <div className={classes.actionButtons}>
            {implementsDelete && isDeleting === followupRequest.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  primary
                  onClick={() => {
                    handleDelete(followupRequest.id);
                  }}
                  size="small"
                  type="submit"
                  data-testid={`deleteRequest_${followupRequest.id}`}
                >
                  Delete
                </Button>
              </div>
            )}
            {!isDone &&
              isSubmitted &&
              implementsGet &&
              !hasRetrieved.includes(followupRequest.id) && (
                <div>
                  {implementsGet && isGetting === followupRequest.id ? (
                    <div>
                      <CircularProgress />
                    </div>
                  ) : (
                    <div>
                      <Button
                        primary
                        onClick={() => {
                          handleGet(followupRequest.id);
                        }}
                        size="small"
                        type="submit"
                        data-testid={`getRequest_${followupRequest.id}`}
                      >
                        Retrieve
                      </Button>
                    </div>
                  )}
                </div>
              )}
            {isFailed && (
              <div>
                {implementSubmit && isSubmitting === followupRequest.id ? (
                  <div>
                    <CircularProgress />
                  </div>
                ) : (
                  <div>
                    <Button
                      primary
                      onClick={() => {
                        handleSubmit(followupRequest);
                      }}
                      size="small"
                      type="submit"
                      data-testid={`submitRequest_${followupRequest.id}`}
                    >
                      Submit
                    </Button>
                  </div>
                )}
              </div>
            )}
            {implementsEdit && (
              <EditFollowupRequestDialog
                followupRequest={followupRequest}
                instrumentFormParams={instrumentFormParams}
                requestType={requestType}
                serverSide={serverSide}
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

    const renderWatcher = (dataIndex) => {
      const followupRequest = requestsGroupedByInstId[instrument_id][dataIndex];
      return (
        <div>
          <WatcherButton
            followupRequest={followupRequest}
            textMode={false}
            serverSide={serverSide}
          />
        </div>
      );
    };
    columns.push({
      name: "watcher",
      label: "Watch?",
      options: {
        customBodyRenderLite: renderWatcher,
      },
    });

    if (serverSide) {
      columns.push({ name: "created_at", label: "Created at" });
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
  };
  if (typeof handleTableChange === "function") {
    options.onTableChange = handleTableChange;
    options.count = totalMatches;
  }
  if (typeof onDownload === "function") {
    options.onDownload = () => {
      onDownload().then((data) => {
        if (data?.length > 0) {
          const head = [
            "obj_id",
            "created_at",
            "requester_id",
            "requester_name",
            "last_modified_by_id",
          ];

          // get all the unique keys from all the requests' payloads
          let keys = data.reduce((r, a) => {
            Object.keys(a.payload).forEach((key) => {
              if (!r.includes(key)) {
                r = [...r, key];
              }
            });
            return r;
          }, []);

          // then reorder the keys so we have start_date, end_date, priority first, in this order
          if (keys.includes("priority")) {
            keys = keys.filter((key) => key !== "priority");
            keys.unshift("priority");
          }
          // then check if payload.end_date is in the keys, if so, remove it and add it to the front
          if (keys.includes("end_date")) {
            keys = keys.filter((key) => key !== "end_date");
            keys.unshift("end_date");
          }
          // then check if payload.start_date is in the keys, if so, remove it and add it to the front
          if (keys.includes("start_date")) {
            keys = keys.filter((key) => key !== "start_date");
            keys.unshift("start_date");
          }

          keys.forEach((key) => {
            head.push(`payload.${key}`);
          });

          head.push(
            "status",
            "allocation_id",
            "allocation_pi",
            "allocation_group_id",
            "allocation_group_name",
            "allocation_types",
          );

          const formatDataFunc = (x) => {
            const formattedData = [
              x.obj_id,
              x.created_at,
              x.requester.id,
              x.requester.username.replaceAll(",", "/"),
              x.last_modified_by_id,
            ];

            keys.forEach((key) => {
              if (key in x.payload) {
                if (Array.isArray(x.payload[key])) {
                  formattedData.push(x.payload[key].join("/"));
                } else if (typeof x.payload[key] === "string") {
                  if (x.payload[key].includes(",")) {
                    formattedData.push(x.payload[key].replaceAll(",", "/"));
                  } else {
                    formattedData.push(x.payload[key]);
                  }
                } else {
                  formattedData.push(x.payload[key]);
                }
              } else {
                formattedData.push("");
              }
            });

            formattedData.push(
              x.status.replaceAll(",", "/"),
              x.allocation.id,
              x.allocation.pi.replaceAll(",", "/"),
              x.allocation.group.id,
              x.allocation.group.name.replaceAll(",", "/"),
              x.allocation.types.join("/"),
            );
            return formattedData;
          };

          const rows = data.map((x) => formatDataFunc(x).join(","));

          const result = `${head.join(",")}\n${rows.join("\n")}`;

          const blob = new Blob([result], {
            type: "text/csv;charset=utf-8;",
          });
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.setAttribute("download", "followup_requests.csv");
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      });
      return false;
    };
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

    // if there is an observation_type, it comes before anything else except dates and priority
    if (
      a === "observation_type" &&
      b !== "end_date" &&
      b !== "start_date" &&
      b !== "priority"
    ) {
      return -1;
    }
    if (
      b === "observation_type" &&
      a !== "end_date" &&
      a !== "start_date" &&
      a !== "priority"
    ) {
      return 1;
    }

    // priority comes before status
    if (a === "priority" && b === "status") {
      return -1;
    }
    if (b === "priority" && a === "status") {
      return 1;
    }

    // priority and status go at the end, so anything else comes before them
    if (a === "priority" || a === "status") {
      return 1;
    }
    if (b === "priority" || b === "status") {
      return -1;
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
              style={{ padding: 0, margin: 0 }}
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
    }),
  ).isRequired,
  instrumentList: PropTypes.arrayOf(
    PropTypes.shape({
      band: PropTypes.string,
      created_at: PropTypes.string,
      id: PropTypes.number,
      name: PropTypes.string,
      type: PropTypes.string,
      telescope_id: PropTypes.number,
    }),
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
  handleTableChange: PropTypes.func,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  showObject: PropTypes.bool,
  serverSide: PropTypes.bool,
  requestType: PropTypes.string,
  onDownload: PropTypes.oneOfType([PropTypes.func, PropTypes.bool]),
};

FollowupRequestLists.defaultProps = {
  showObject: false,
  serverSide: false,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  handleTableChange: null,
  requestType: "triggered",
  onDownload: false,
};
export default FollowupRequestLists;

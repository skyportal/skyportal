import { useState } from "react";
import { JSONTree } from "react-json-tree";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DownloadIcon from "@mui/icons-material/Download";
import { makeStyles } from "tss-react/mui";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarQuickFilter,
  GridToolbarExport,
} from "@mui/x-data-grid";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import WatcherButton from "./WatcherButton";

import {
  useDeleteFollowupRequestMutation,
  useEditFollowupRequestMutation,
  useLazyGetPhotometryRequestQuery,
} from "../../ducks/source";

import EditFollowupRequestDialog from "./EditFollowupRequestDialog";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const useStyles = makeStyles()(() => ({
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

// Labels (lower-cased) of payload-derived columns that should be visible by
// default. Mirrors the previous mui-datatables `display` list.
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

interface FollowupRequestListsProps {
  followupRequests: any[];
  instrumentList: any[];
  instrumentFormParams: any;
  totalMatches?: number;
  handleTableChange?: ((...a: any[]) => void) | boolean;
  pageNumber?: number;
  numPerPage?: number;
  showObject?: boolean;
  serverSide?: boolean;
  requestType?: string;
  onDownload?: ((...a: any[]) => any) | boolean;
}

const FollowupRequestLists = ({
  followupRequests,
  instrumentList,
  instrumentFormParams,
  totalMatches = 0,
  handleTableChange = false,
  pageNumber = 1,
  numPerPage = 10,
  showObject = false,
  serverSide = false,
  requestType = "triggered",
  onDownload = false,
}: FollowupRequestListsProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [deleteFollowupRequestMutation] = useDeleteFollowupRequestMutation();
  const [editFollowupRequestMutation] = useEditFollowupRequestMutation();
  const [getPhotometryRequest] = useLazyGetPhotometryRequestQuery();

  const [isDeleting, setIsDeleting] = useState<any>(null);
  const [isGetting, setIsGetting] = useState<any>(null);
  const [hasRetrieved, setHasRetrieved] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<any>(null);
  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  // Per-instrument column visibility model, keyed by instrument_id.
  const [columnVisibilityModels, setColumnVisibilityModels] = useState<any>({});

  const handleDelete = async (id: any) => {
    setIsDeleting(id);
    const params: any = {};
    if (serverSide) {
      params.refreshRequests = true;
    }
    await deleteFollowupRequestMutation({ id, params });
    setIsDeleting(null);
  };

  const handleGet = async (id: any) => {
    setIsGetting(id);
    const params: any = {};
    if (serverSide) {
      params.refreshRequests = true;
    }
    try {
      const data: any = await getPhotometryRequest({ id, params }).unwrap();
      setIsGetting(null);
      if (data?.request_status?.includes("rejected")) {
        dispatch(showNotification("Request has been rejected.", "warning"));
      } else {
        dispatch(
          showNotification(
            "Request successfully submitted, please wait for it to be processed.",
            "info",
          ),
        );
      }
      setHasRetrieved([...hasRetrieved, id]);
    } catch {
      setIsGetting(null);
    }
  };

  const handleSubmit = async (followupRequest: any) => {
    setIsSubmitting(followupRequest.id);
    const json: any = {
      allocation_id: followupRequest.allocation.id,
      obj_id: followupRequest.obj_id,
      payload: followupRequest.payload,
    };
    if (serverSide) {
      json.refreshRequests = true;
    }
    await editFollowupRequestMutation({
      params: json,
      requestID: followupRequest.id,
    });
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

  const instLookUp = instrumentList.reduce((r: any, a: any) => {
    r[a.id] = a;
    return r;
  }, {});

  if (!Array.isArray(followupRequests)) {
    return <p>Waiting for followup requests to load...</p>;
  }

  const requestsGroupedByInstId = followupRequests.reduce((r: any, a: any) => {
    r[a.allocation.instrument.id] = [
      ...(r[a.allocation.instrument.id] || []),
      a,
    ];
    return r;
  }, {});

  // Build DataGrid columns and a default column-visibility model for one
  // instrument group. Returns { columns, defaultVisibility }.
  const getDataTableColumns = (keys: any[], instrument_id: any) => {
    const columns: any[] = [
      {
        field: "requester.username",
        headerName: "Requester",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => row.requester?.username,
      },
      {
        field: "allocation.group.name",
        headerName: "Group",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => row.allocation?.group?.name,
      },
      {
        field: "allocation.pi",
        headerName: "PI",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => row.allocation?.pi,
      },
    ];
    const defaultVisibility: any = {};

    if (!(instrument_id in instrumentFormParams)) {
      return { columns, defaultVisibility };
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

    if (
      instrumentFormParams[instrument_id]?.formSchema?.properties?.station_name
    ) {
      columns.push({
        field: "station",
        headerName: "Station",
        flex: 1,
        minWidth: 120,
        sortable: false,
        filterable: false,
        valueGetter: (_value: any, row: any) => row?.payload?.station_name,
      });
    }

    if (showObject) {
      columns.push({
        field: "obj",
        headerName: "Object",
        flex: 1,
        minWidth: 120,
        filterable: false,
        valueGetter: (_value: any, row: any) => row.obj?.id,
        renderCell: (params: any) => {
          const followupRequest = params.row;
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
        },
      });
    }

    keys?.forEach((key) => {
      const field = Object.keys(
        instrumentFormParams[instrument_id].aliasLookup,
      ).includes(key)
        ? instrumentFormParams[instrument_id].aliasLookup[key]
        : key;
      const colField = `payload.${key}`;
      columns.push({
        field: colField,
        headerName: field,
        flex: 1,
        minWidth: 120,
        sortable: false,
        filterable: false,
        valueGetter: (_value: any, row: any) => {
          const v = row.payload?.[key];
          return Array.isArray(v) ? v.join(",") : v;
        },
      });
      if (!displayedColumns.includes(field.toLowerCase())) {
        defaultVisibility[colField] = false;
      }
    });

    columns.push({
      field: "status",
      headerName: "Status",
      minWidth: 250,
      flex: 1,
    });

    columns.push({
      field: "Transactions",
      headerName: "Transactions",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => {
        const followupRequest = params.row;
        return (
          <div style={{ whiteSpace: "nowrap" }}>
            {followupRequest ? (
              <JSONTree data={followupRequest.transactions} hideRoot />
            ) : (
              ""
            )}
          </div>
        );
      },
    });
    defaultVisibility.Transactions = false;

    if (modifiable) {
      columns.push({
        field: "modify",
        headerName: "Modify",
        flex: 1,
        minWidth: 140,
        sortable: false,
        filterable: false,
        renderCell: (params: any) => {
          const followupRequest = params.row;

          const isDone =
            followupRequest.status === "Photometry committed to database";

          const isSubmitted =
            followupRequest.status.startsWith("pending") ||
            followupRequest.status.startsWith("submitted");

          const isFailed = followupRequest.status.includes("failed to submit");

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
        },
      });
    }

    columns.push({
      field: "watcher",
      headerName: "Watch?",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => (
        <div>
          <WatcherButton
            followupRequest={params.row}
            textMode={false}
            serverSide={serverSide}
          />
        </div>
      ),
    });

    if (serverSide) {
      columns.push({
        field: "created_at",
        headerName: "Created at",
        flex: 1,
        minWidth: 150,
      });
    }

    return { columns, defaultVisibility };
  };

  // Synthesize the mui-datatables onTableChange(action, tableState) contract
  // from the DataGrid handlers so callers stay unchanged.
  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    if (typeof handleTableChange === "function") {
      handleTableChange("changePage", {
        page: model.page,
        rowsPerPage: model.pageSize,
        sortOrder: { direction: "none" },
      });
    }
  };

  const handleDownload = () => {
    if (typeof onDownload !== "function") {
      return;
    }
    onDownload().then((data: any) => {
      if (!data?.length) {
        return;
      }
      const head = [
        "obj_id",
        "created_at",
        "requester_id",
        "requester_name",
        "last_modified_by_id",
      ];

      // get all the unique keys from all the requests' payloads
      let keys = data.reduce((r: any, a: any) => {
        Object.keys(a.payload).forEach((key) => {
          if (!r.includes(key)) {
            r = [...r, key];
          }
        });
        return r;
      }, []);

      // then reorder the keys so we have start_date, end_date, priority first, in this order
      if (keys.includes("priority")) {
        keys = keys.filter((key: any) => key !== "priority");
        keys.unshift("priority");
      }
      // then check if payload.end_date is in the keys, if so, remove it and add it to the front
      if (keys.includes("end_date")) {
        keys = keys.filter((key: any) => key !== "end_date");
        keys.unshift("end_date");
      }
      // then check if payload.start_date is in the keys, if so, remove it and add it to the front
      if (keys.includes("start_date")) {
        keys = keys.filter((key: any) => key !== "start_date");
        keys.unshift("start_date");
      }

      keys.forEach((key: any) => {
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

      const formatDataFunc = (x: any) => {
        const formattedData = [
          x.obj_id,
          x.created_at,
          x.requester.id,
          x.requester.username.replaceAll(",", "/"),
          x.last_modified_by_id,
        ];

        keys.forEach((key: any) => {
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

      const rows = data.map((x: any) => formatDataFunc(x).join(","));

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
      URL.revokeObjectURL(url);
    });
  };

  const showDownload = typeof onDownload === "function";

  const makeToolbar = () =>
    function FollowupRequestToolbar() {
      return (
        <GridToolbarContainer>
          <GridToolbarColumnsButton />
          <GridToolbarExport />
          {showDownload && (
            <Tooltip title="Download CSV">
              <IconButton
                size="small"
                aria-label="Download CSV"
                data-testid="download-followup-requests-button"
                onClick={handleDownload}
              >
                <DownloadIcon />
              </IconButton>
            </Tooltip>
          )}
          <GridToolbarQuickFilter />
        </GridToolbarContainer>
      );
    };

  const keyOrder = (a: any, b: any) => {
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
        const keys = requestsGroupedByInstId[instrument_id].reduce(
          (r: any, a: any) => {
            Object.keys(a.payload).forEach((key) => {
              if (!r.includes(key)) {
                r = [...r, key];
              }
            });
            return r;
          },
          [],
        );

        keys.sort(keyOrder);

        const { columns, defaultVisibility } = getDataTableColumns(
          keys,
          instrument_id,
        );

        const visibilityModel =
          columnVisibilityModels[instrument_id] ?? defaultVisibility;

        const CustomToolbar = makeToolbar();

        return (
          <Accordion
            className={classes.accordion}
            key={`instrument_${instrument_id}_table_div`}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls={`${instLookUp[instrument_id].name}-requests`}
              data-testid={`${instrument_id}-requests-header`}
            >
              <Typography variant="subtitle1">
                {instLookUp[instrument_id].name} Requests
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              data-testid={`${instrument_id}_followupRequestsTable`}
              style={{ padding: 0, margin: 0 }}
            >
              <Box sx={{ width: "100%" }}>
                <StyledDataGrid
                  autoHeight
                  rows={requestsGroupedByInstId[instrument_id]}
                  columns={columns}
                  getRowId={(row: any) => row.id}
                  columnVisibilityModel={visibilityModel}
                  onColumnVisibilityModelChange={(model: any) =>
                    setColumnVisibilityModels((prev: any) => ({
                      ...prev,
                      [instrument_id]: model,
                    }))
                  }
                  paginationMode={serverSide ? "server" : "client"}
                  rowCount={serverSide ? totalMatches : undefined}
                  paginationModel={
                    serverSide
                      ? { page: pageNumber - 1, pageSize: rowsPerPage }
                      : undefined
                  }
                  onPaginationModelChange={
                    serverSide ? handlePaginationModelChange : undefined
                  }
                  initialState={
                    serverSide
                      ? undefined
                      : {
                          pagination: {
                            paginationModel: { pageSize: numPerPage },
                          },
                        }
                  }
                  pageSizeOptions={PAGE_SIZE_OPTIONS}
                  slots={{ toolbar: CustomToolbar }}
                  showToolbar
                />
              </Box>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </div>
  );
};

export default FollowupRequestLists;

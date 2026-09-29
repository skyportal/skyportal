import { useState } from "react";
import { Link } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DownloadIcon from "@mui/icons-material/Download";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import WatcherButton from "./WatcherButton";
import JsonCell from "./JsonCell";

import {
  useDeleteFollowupRequestMutation,
  useEditFollowupRequestMutation,
  useLazyGetPhotometryRequestQuery,
} from "../../ducks/source";

import EditFollowupRequestDialog from "./EditFollowupRequestDialog";

const DISPLAYED_COLUMNS = [
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

const KEY_RANK: Record<string, number> = {
  start_date: 0,
  end_date: 1,
  observation_type: 2,
  priority: 4,
  status: 5,
};

const keyOrder = (a: string, b: string) =>
  (KEY_RANK[a] ?? 3) - (KEY_RANK[b] ?? 3) || (a < b ? -1 : Number(a > b));

const statusColor = (status: string) => {
  if (/fail|reject|error/i.test(status)) return "error";
  if (/complete|committed/i.test(status)) return "success";
  if (/submitted/i.test(status)) return "primary";
  if (/pending/i.test(status)) return "warning";
  return "default";
};

const CSV_FIRST_KEYS = ["start_date", "end_date", "priority"];

const csvValue = (value: any) => {
  if (Array.isArray(value)) return value.join("/");
  return typeof value === "string" ? value.replaceAll(",", "/") : value;
};

const downloadRequestsCsv = async (onDownload: () => Promise<any[]>) => {
  const data = await onDownload();
  if (!data?.length) return;
  const payloadKeys = [
    ...new Set(data.flatMap((request) => Object.keys(request.payload))),
  ];
  const keys = [
    ...CSV_FIRST_KEYS.filter((key) => payloadKeys.includes(key)),
    ...payloadKeys.filter((key) => !CSV_FIRST_KEYS.includes(key)),
  ];
  const head = [
    "obj_id",
    "created_at",
    "requester_id",
    "requester_name",
    "last_modified_by_id",
    ...keys.map((key) => `payload.${key}`),
    "status",
    "allocation_id",
    "allocation_pi",
    "allocation_group_id",
    "allocation_group_name",
    "allocation_types",
  ];
  const rows = data.map((request) =>
    [
      request.obj_id,
      request.created_at,
      request.requester.id,
      request.requester.username,
      request.last_modified_by_id,
      ...keys.map((key) =>
        key in request.payload ? request.payload[key] : "",
      ),
      request.status,
      request.allocation.id,
      request.allocation.pi,
      request.allocation.group.id,
      request.allocation.group.name,
      request.allocation.types,
    ]
      .map(csvValue)
      .join(","),
  );

  const url = URL.createObjectURL(
    new Blob([`${head.join(",")}\n${rows.join("\n")}`], {
      type: "text/csv;charset=utf-8;",
    }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", "followup_requests.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const FollowupRequestToolbar = ({
  onDownload,
}: {
  onDownload?: () => Promise<any[]>;
}) => (
  <DataGridToolbar showExport={false} showExpandAll>
    {onDownload && (
      <Tooltip title="Download CSV">
        <IconButton
          size="small"
          aria-label="Download CSV"
          onClick={() => downloadRequestsCsv(onDownload)}
        >
          <DownloadIcon />
        </IconButton>
      </Tooltip>
    )}
  </DataGridToolbar>
);

const ActionButton = ({
  loading = false,
  onClick,
  testId,
  children,
}: {
  loading?: boolean;
  onClick: () => void;
  testId?: string;
  children: string;
}) =>
  loading ? (
    <CircularProgress />
  ) : (
    <Button
      primary
      size="small"
      type="submit"
      onClick={onClick}
      data-testid={testId}
    >
      {children}
    </Button>
  );

interface FollowupRequestListsProps {
  followupRequests: any[];
  instrumentList: any[];
  instrumentFormParams: any;
  totalMatches?: number;
  onPaginationChange?: (page: number, pageSize: number) => void;
  pageNumber?: number;
  numPerPage?: number;
  showObject?: boolean;
  serverSide?: boolean;
  requestType?: string;
  onDownload?: () => Promise<any[]>;
}

const FollowupRequestLists = ({
  followupRequests,
  instrumentList,
  instrumentFormParams,
  totalMatches = 0,
  onPaginationChange,
  pageNumber = 1,
  numPerPage = 25,
  showObject = false,
  serverSide = false,
  requestType = "triggered",
  onDownload,
}: FollowupRequestListsProps) => {
  const dispatch = useAppDispatch();
  const [deleteFollowupRequestMutation] = useDeleteFollowupRequestMutation();
  const [editFollowupRequestMutation] = useEditFollowupRequestMutation();
  const [getPhotometryRequest] = useLazyGetPhotometryRequestQuery();

  const [isDeleting, setIsDeleting] = useState<number | null>(null);
  const [isGetting, setIsGetting] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<number | null>(null);
  const [hasRetrieved, setHasRetrieved] = useState<number[]>([]);
  // Not in the cell: its DataGrid column is virtualized, a remount would close the dialog.
  const [requestIdToEdit, setRequestIdToEdit] = useState<number | null>(null);
  const [columnVisibilityModels, setColumnVisibilityModels] = useState<
    Record<string, any>
  >({});
  const refresh = serverSide ? { refreshRequests: true } : {};

  const handleDelete = async (id: number) => {
    setIsDeleting(id);
    await deleteFollowupRequestMutation({ id, params: refresh });
    setIsDeleting(null);
  };

  const handleGet = async (id: number) => {
    setIsGetting(id);
    const { data, error }: any = await getPhotometryRequest({
      id,
      params: refresh,
    });
    setIsGetting(null);
    if (error) return;
    dispatch(
      data?.request_status?.includes("rejected")
        ? showNotification("Request has been rejected.", "warning")
        : showNotification(
            "Request successfully submitted, please wait for it to be processed.",
            "info",
          ),
    );
    setHasRetrieved((ids) => [...ids, id]);
  };

  const handleSubmit = async (followupRequest: any) => {
    setIsSubmitting(followupRequest.id);
    await editFollowupRequestMutation({
      params: {
        allocation_id: followupRequest.allocation.id,
        obj_id: followupRequest.obj_id,
        payload: followupRequest.payload,
        ...refresh,
      },
      requestID: followupRequest.id,
    });
    setIsSubmitting(null);
  };

  if (requestType === "triggered" || requestType === "forced_photometry") {
    const [schema, otherSchema] =
      requestType === "triggered"
        ? ["formSchema", "formSchemaForcedPhotometry"]
        : ["formSchemaForcedPhotometry", "formSchema"];
    instrumentList = instrumentList.filter(
      (inst) => instrumentFormParams[inst.id]?.[schema] != null,
    );
    followupRequests = followupRequests.filter(
      (request) =>
        request?.payload?.request_type === requestType ||
        (request?.allocation?.instrument_id in instrumentFormParams &&
          instrumentFormParams[request.allocation.instrument_id]?.[
            otherSchema
          ] == null),
    );
  }

  if (
    !followupRequests.length ||
    (!serverSide &&
      (!instrumentList.length || !Object.keys(instrumentFormParams).length))
  ) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No follow-up requests found.
      </Typography>
    );
  }

  const instLookUp = Object.fromEntries(
    instrumentList.map((inst: any) => [inst.id, inst]),
  );

  const requestsGroupedByInstId = followupRequests.reduce(
    (grouped: any, request: any) => {
      (grouped[request.allocation.instrument.id] ||= []).push(request);
      return grouped;
    },
    {},
  );

  const getDataTableColumns = (keys: string[], instrument_id: string) => {
    const columns: any[] = [
      {
        field: "requester.username",
        headerName: "Requester",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => row.requester?.username,
        renderCell: ({ row, value }: any) => (
          <Link to={`/user/${row.requester?.id}`}>{value}</Link>
        ),
      },
      {
        field: "allocation.group.name",
        headerName: "Group",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => row.allocation?.group?.name,
        renderCell: ({ row, value }: any) => (
          <Link to={`/group/${row.allocation?.group?.id}`}>{value}</Link>
        ),
      },
      {
        field: "allocation.pi",
        headerName: "PI",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => row.allocation?.pi,
        renderCell: ({ row, value }: any) => (
          <Link to={`/allocation/${row.allocation?.id}`}>{value}</Link>
        ),
      },
    ];
    const defaultVisibility: Record<string, boolean> = { Transactions: false };

    const formParams = instrumentFormParams[instrument_id];
    if (!formParams) return { columns, defaultVisibility: {} };
    const {
      submit: implementsSubmit,
      delete: implementsDelete,
      get: implementsGet,
    } = formParams.methodsImplemented;
    const implementsEdit =
      formParams.methodsImplemented.update && requestType === "triggered";

    if (formParams.formSchema?.properties?.station_name) {
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
        renderCell: ({ value }: any) => (
          <Link to={`/source/${value}`}>{value}</Link>
        ),
      });
    }

    keys.forEach((key) => {
      const headerName = formParams.aliasLookup[key] ?? key;
      const field = `payload.${key}`;
      columns.push({
        field,
        headerName,
        flex: 1,
        minWidth: 120,
        sortable: false,
        filterable: false,
        valueGetter: (_value: any, row: any) => {
          const value = row.payload?.[key];
          return Array.isArray(value) ? value.join(",") : value;
        },
      });
      if (!DISPLAYED_COLUMNS.includes(headerName.toLowerCase())) {
        defaultVisibility[field] = false;
      }
    });

    columns.push(
      {
        field: "status",
        headerName: "Status",
        minWidth: 250,
        flex: 1,
        renderCell: ({ value }: any) => (
          <Tooltip title={value}>
            <Chip
              size="small"
              variant="outlined"
              label={value}
              color={statusColor(value)}
              sx={{ maxWidth: "100%" }}
            />
          </Tooltip>
        ),
      },
      {
        field: "Transactions",
        headerName: "Transactions",
        flex: 1,
        minWidth: 150,
        sortable: false,
        filterable: false,
        renderCell: ({ row }: any) => <JsonCell data={row.transactions} />,
      },
    );

    if (implementsEdit || implementsDelete || implementsGet) {
      columns.push({
        field: "modify",
        headerName: "Modify",
        flex: 1,
        minWidth: 140,
        sortable: false,
        filterable: false,
        renderCell: ({ row }: any) => {
          const isDeleted = row.status === "deleted";
          const canRetrieve =
            implementsGet &&
            row.status !== "Photometry committed to database" &&
            (row.status.startsWith("pending") ||
              row.status.startsWith("submitted")) &&
            !hasRetrieved.includes(row.id);

          return (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.25, py: 0.5 }}>
              {implementsDelete && !isDeleted && (
                <ActionButton
                  loading={isDeleting === row.id}
                  onClick={() => handleDelete(row.id)}
                  testId={`deleteRequest_${row.id}`}
                >
                  Delete
                </ActionButton>
              )}
              {canRetrieve && (
                <ActionButton
                  loading={isGetting === row.id}
                  onClick={() => handleGet(row.id)}
                >
                  Retrieve
                </ActionButton>
              )}
              {implementsSubmit && row.status.includes("failed to submit") && (
                <ActionButton
                  loading={isSubmitting === row.id}
                  onClick={() => handleSubmit(row)}
                >
                  Submit
                </ActionButton>
              )}
              {implementsEdit && !isDeleted && (
                <ActionButton
                  onClick={() => setRequestIdToEdit(row.id)}
                  testId={`editRequest_${row.id}`}
                >
                  Edit
                </ActionButton>
              )}
            </Box>
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
      renderCell: ({ row }: any) => (
        <WatcherButton followupRequest={row} serverSide={serverSide} />
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

  const requestToEdit = followupRequests.find(
    (request: any) => request.id === requestIdToEdit,
  );

  return (
    <Box sx={{ m: "0 1px 1px 1px" }}>
      {requestToEdit && (
        <EditFollowupRequestDialog
          followupRequest={requestToEdit}
          instrumentFormParams={instrumentFormParams}
          onClose={() => setRequestIdToEdit(null)}
          requestType={requestType}
          serverSide={serverSide}
        />
      )}
      {Object.entries(requestsGroupedByInstId).map(
        ([instrument_id, requests]: [string, any]) => {
          const keys = [
            ...new Set<string>(
              requests.flatMap((request: any) => Object.keys(request.payload)),
            ),
          ].sort(keyOrder);
          const { columns, defaultVisibility } = getDataTableColumns(
            keys,
            instrument_id,
          );

          return (
            <Accordion
              defaultExpanded
              sx={{ width: "100%" }}
              key={instrument_id}
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
                sx={{ p: 0, m: 0 }}
              >
                <StyledDataGrid
                  height="auto"
                  getRowHeight={() => "auto"}
                  sx={{
                    "& .MuiDataGrid-cell a:not(.MuiLink-root):not(.MuiButtonBase-root)":
                      {
                        color: "inherit",
                        fontWeight: "inherit",
                        "&:hover": { textDecoration: "underline" },
                      },
                  }}
                  rows={requests}
                  columns={columns}
                  columnVisibilityModel={
                    columnVisibilityModels[instrument_id] ?? defaultVisibility
                  }
                  onColumnVisibilityModelChange={(model: any) =>
                    setColumnVisibilityModels((prev) => ({
                      ...prev,
                      [instrument_id]: model,
                    }))
                  }
                  {...(serverSide
                    ? {
                        paginationMode: "server",
                        rowCount: totalMatches,
                        paginationModel: {
                          page: pageNumber - 1,
                          pageSize: numPerPage,
                        },
                        onPaginationModelChange: ({ page, pageSize }: any) =>
                          onPaginationChange?.(page, pageSize),
                      }
                    : {
                        initialState: {
                          pagination: {
                            paginationModel: { pageSize: numPerPage },
                          },
                        },
                      })}
                  slots={{ toolbar: FollowupRequestToolbar }}
                  slotProps={{ toolbar: { onDownload } }}
                  showToolbar
                />
              </AccordionDetails>
            </Accordion>
          );
        },
      )}
    </Box>
  );
};

export default FollowupRequestLists;

import { useState } from "react";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import { ToolbarButton } from "@mui/x-data-grid";
import DownloadIcon from "@mui/icons-material/Download";
import EventNoteIcon from "@mui/icons-material/EventNote";
import LowPriorityIcon from "@mui/icons-material/LowPriority";

import { useGetInstrumentFormsQuery } from "../../ducks/instruments";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import EditFollowupRequestDialog from "./EditFollowupRequestDialog";
import FollowupPrioritizationDialog from "./FollowupPrioritizationDialog";
import FollowupRequestActions from "./FollowupRequestActions";
import FollowupScheduleDialog from "./FollowupScheduleDialog";
import JsonCell from "./JsonCell";
import {
  PLAIN_LINKS_SX,
  allocationColumn,
  groupColumn,
  objectColumn,
  requesterColumn,
  statusColumn,
  transactionsColumn,
  watcherColumn,
} from "./columns";

dayjs.extend(utc);

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

const ToolbarAction = ({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick: () => void;
  children: any;
}) => (
  <Tooltip title={title}>
    <ToolbarButton aria-label={title} onClick={onClick}>
      {children}
    </ToolbarButton>
  </Tooltip>
);

const FollowupRequestTableToolbar = ({
  onDownload,
  onSchedule,
  onPrioritize,
}: {
  onDownload: () => void;
  onSchedule: () => void;
  onPrioritize: () => void;
}) => (
  <DataGridToolbar
    title="Follow-up Requests"
    showExport={false}
    showQuickFilter={false}
    showExpandAll
  >
    <ToolbarAction title="Download CSV" onClick={onDownload}>
      <DownloadIcon fontSize="small" />
    </ToolbarAction>
    <ToolbarAction title="Schedule" onClick={onSchedule}>
      <EventNoteIcon fontSize="small" />
    </ToolbarAction>
    <ToolbarAction title="Prioritize" onClick={onPrioritize}>
      <LowPriorityIcon fontSize="small" />
    </ToolbarAction>
  </DataGridToolbar>
);

const requestTypeOf = (request: any) =>
  request.payload?.request_type === "forced_photometry"
    ? "forced_photometry"
    : "triggered";

interface FollowupRequestTableProps {
  requests: any[];
  totalMatches: number;
  loading: boolean;
  paginationModel: { page: number; pageSize: number };
  onPaginationModelChange: (model: { page: number; pageSize: number }) => void;
  sortModel: any[];
  onSortModelChange: (model: any[]) => void;
  onDownload: () => Promise<any[]>;
}

const FollowupRequestTable = ({
  requests,
  totalMatches,
  loading,
  paginationModel,
  onPaginationModelChange,
  sortModel,
  onSortModelChange,
  onDownload,
}: FollowupRequestTableProps) => {
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const [dialog, setDialog] = useState<"schedule" | "prioritize" | null>(null);
  const [requestIdToEdit, setRequestIdToEdit] = useState<number | null>(null);
  const requestToEdit = requests.find(({ id }) => id === requestIdToEdit);

  const columns: any[] = [
    {
      field: "created_at",
      headerName: "Created",
      minWidth: 150,
      valueFormatter: (value: string) =>
        dayjs.utc(value).format("YYYY-MM-DD HH:mm"),
    },
    objectColumn,
    {
      field: "instrument",
      headerName: "Instrument",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (_value: any, row: any) => row.allocation?.instrument?.name,
    },
    { ...allocationColumn, sortable: false },
    { ...groupColumn, sortable: false },
    { ...requesterColumn, sortable: false },
    {
      field: "priority",
      headerName: "Priority",
      minWidth: 80,
      sortable: false,
      valueGetter: (_value: any, row: any) => row.payload?.priority,
    },
    {
      field: "payload",
      headerName: "Payload",
      flex: 2,
      minWidth: 220,
      sortable: false,
      valueGetter: (_value: any, row: any) => {
        const { priority, ...payload } = row.payload ?? {};
        return payload;
      },
      renderCell: ({ value }: any) => <JsonCell data={value} />,
    },
    statusColumn,
    { ...transactionsColumn, sortable: false },
    {
      field: "actions",
      headerName: "Actions",
      minWidth: 140,
      sortable: false,
      renderCell: ({ row }: any) => {
        const methodsImplemented =
          instrumentFormParams[row.allocation.instrument_id]
            ?.methodsImplemented;
        if (!methodsImplemented) return null;
        return (
          <FollowupRequestActions
            request={row}
            methodsImplemented={methodsImplemented}
            editable={
              methodsImplemented.update && requestTypeOf(row) === "triggered"
            }
            refresh
            onEdit={setRequestIdToEdit}
          />
        );
      },
    },
    watcherColumn(true),
  ];

  return (
    <Box data-testid="followup-requests-table">
      <StyledDataGrid
        height="auto"
        getRowHeight={() => "auto"}
        sx={PLAIN_LINKS_SX}
        rows={requests}
        columns={columns}
        loading={loading}
        localeText={{ noRowsLabel: "No follow-up requests found." }}
        paginationMode="server"
        rowCount={totalMatches}
        paginationModel={paginationModel}
        onPaginationModelChange={onPaginationModelChange}
        sortingMode="server"
        sortModel={sortModel}
        onSortModelChange={onSortModelChange}
        disableColumnFilter
        initialState={{
          columns: { columnVisibilityModel: { Transactions: false } },
        }}
        slots={{ toolbar: FollowupRequestTableToolbar }}
        slotProps={{
          toolbar: {
            onDownload: () => downloadRequestsCsv(onDownload),
            onSchedule: () => setDialog("schedule"),
            onPrioritize: () => setDialog("prioritize"),
          },
        }}
        showToolbar
      />
      {requestToEdit && (
        <EditFollowupRequestDialog
          followupRequest={requestToEdit}
          instrumentFormParams={instrumentFormParams}
          onClose={() => setRequestIdToEdit(null)}
          requestType={requestTypeOf(requestToEdit)}
          serverSide
        />
      )}
      <FollowupScheduleDialog
        open={dialog === "schedule"}
        onClose={() => setDialog(null)}
      />
      <FollowupPrioritizationDialog
        open={dialog === "prioritize"}
        onClose={() => setDialog(null)}
        followupRequests={requests}
      />
    </Box>
  );
};

export default FollowupRequestTable;

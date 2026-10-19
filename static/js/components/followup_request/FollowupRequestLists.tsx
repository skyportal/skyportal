import { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import EditFollowupRequestDialog from "./EditFollowupRequestDialog";
import FollowupRequestActions from "./FollowupRequestActions";
import {
  PLAIN_LINKS_SX,
  allocationColumn,
  groupColumn,
  requesterColumn,
  statusColumn,
  transactionsColumn,
  watcherColumn,
} from "./columns";

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

const FollowupRequestListToolbar = () => (
  <DataGridToolbar showExport={false} showExpandAll />
);

interface FollowupRequestListsProps {
  followupRequests: any[];
  instrumentList: any[];
  instrumentFormParams: any;
  requestType?: string;
}

const FollowupRequestLists = ({
  followupRequests,
  instrumentList,
  instrumentFormParams,
  requestType = "triggered",
}: FollowupRequestListsProps) => {
  // Not in the cell: its DataGrid column is virtualized, a remount would close the dialog.
  const [requestIdToEdit, setRequestIdToEdit] = useState<number | null>(null);
  const [columnVisibilityModels, setColumnVisibilityModels] = useState<
    Record<string, any>
  >({});

  const [schema, otherSchema] =
    requestType === "triggered"
      ? ["formSchema", "formSchemaForcedPhotometry"]
      : ["formSchemaForcedPhotometry", "formSchema"];
  const instruments = instrumentList.filter(
    (inst) => instrumentFormParams[inst.id]?.[schema] != null,
  );
  const requests = followupRequests.filter(
    (request) =>
      request?.payload?.request_type === requestType ||
      (request?.allocation?.instrument_id in instrumentFormParams &&
        instrumentFormParams[request.allocation.instrument_id]?.[otherSchema] ==
          null),
  );

  if (!requests.length || !instruments.length) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No follow-up requests found.
      </Typography>
    );
  }

  const instLookUp = Object.fromEntries(
    instruments.map((inst: any) => [inst.id, inst]),
  );
  const requestsGroupedByInstId = requests.reduce(
    (grouped: any, request: any) => {
      (grouped[request.allocation.instrument.id] ||= []).push(request);
      return grouped;
    },
    {},
  );

  const getDataTableColumns = (keys: string[], instrument_id: string) => {
    const columns: any[] = [requesterColumn, groupColumn, allocationColumn];
    const formParams = instrumentFormParams[instrument_id];
    if (!formParams) return { columns, defaultVisibility: {} };
    const defaultVisibility: Record<string, boolean> = { Transactions: false };
    const { methodsImplemented } = formParams;
    const editable = methodsImplemented.update && requestType === "triggered";

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

    columns.push(statusColumn, transactionsColumn);

    if (editable || methodsImplemented.delete || methodsImplemented.get) {
      columns.push({
        field: "modify",
        headerName: "Modify",
        flex: 1,
        minWidth: 140,
        sortable: false,
        filterable: false,
        renderCell: ({ row }: any) => (
          <FollowupRequestActions
            request={row}
            methodsImplemented={methodsImplemented}
            editable={editable}
            refresh={false}
            onEdit={setRequestIdToEdit}
          />
        ),
      });
    }

    columns.push(watcherColumn(false));
    return { columns, defaultVisibility };
  };

  const requestToEdit = requests.find(
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
        />
      )}
      {Object.entries(requestsGroupedByInstId).map(
        ([instrument_id, instrumentRequests]: [string, any]) => {
          const keys = [
            ...new Set<string>(
              instrumentRequests.flatMap((request: any) =>
                Object.keys(request.payload),
              ),
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
                aria-controls={`${instLookUp[instrument_id]?.name}-requests`}
                data-testid={`${instrument_id}-requests-header`}
              >
                <Typography variant="subtitle1">
                  {instLookUp[instrument_id]?.name} Requests
                </Typography>
              </AccordionSummary>
              <AccordionDetails
                data-testid={`${instrument_id}_followupRequestsTable`}
                sx={{ p: 0, m: 0 }}
              >
                <StyledDataGrid
                  height="auto"
                  getRowHeight={() => "auto"}
                  sx={PLAIN_LINKS_SX}
                  rows={instrumentRequests}
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
                  slots={{ toolbar: FollowupRequestListToolbar }}
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

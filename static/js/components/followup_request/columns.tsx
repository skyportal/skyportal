import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

import JsonCell from "./JsonCell";
import WatcherButton from "./WatcherButton";
import { statusColor } from "./status";

export const PLAIN_LINKS_SX = {
  "& .MuiDataGrid-cell a:not(.MuiLink-root):not(.MuiButtonBase-root)": {
    color: "inherit",
    fontWeight: "inherit",
    "&:hover": { textDecoration: "underline" },
  },
};

const linkColumn = (
  field: string,
  headerName: string,
  getValue: (row: any) => any,
  getPath: (row: any) => string,
) => ({
  field,
  headerName,
  flex: 1,
  minWidth: 120,
  valueGetter: (_value: any, row: any) => getValue(row),
  renderCell: ({ row, value }: any) => <Link to={getPath(row)}>{value}</Link>,
});

export const requesterColumn = linkColumn(
  "requester.username",
  "Requester",
  (row) => row.requester?.username,
  (row) => `/user/${row.requester?.id}`,
);

export const groupColumn = linkColumn(
  "allocation.group.name",
  "Group",
  (row) => row.allocation?.group?.name,
  (row) => `/group/${row.allocation?.group?.id}`,
);

export const allocationColumn = linkColumn(
  "allocation.pi",
  "PI",
  (row) => row.allocation?.pi,
  (row) => `/allocation/${row.allocation?.id}`,
);

export const objectColumn = linkColumn(
  "obj",
  "Object",
  (row) => row.obj_id,
  (row) => `/source/${row.obj_id}`,
);

export const statusColumn = {
  field: "status",
  headerName: "Status",
  flex: 1,
  minWidth: 150,
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
};

export const transactionsColumn = {
  field: "Transactions",
  headerName: "Transactions",
  flex: 1,
  minWidth: 150,
  sortable: false,
  filterable: false,
  renderCell: ({ row }: any) => <JsonCell data={row.transactions} />,
};

export const watcherColumn = (refresh: boolean) => ({
  field: "watcher",
  headerName: "Watch?",
  minWidth: 80,
  sortable: false,
  filterable: false,
  renderCell: ({ row }: any) => (
    <WatcherButton followupRequest={row} refresh={refresh} />
  ),
});

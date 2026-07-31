import { useEffect, useState } from "react";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

export interface AlertRow {
  id: string;
  objectId: string;
  candid?: string | number;
  jd?: number;
  ra?: number;
  dec?: number;
  band?: string | number;
  magpsf?: number;
  sigmapsf?: number;
  snr?: number;
  isdiffpos?: string | boolean;
  drb?: number;
  programid?: number;
  separation?: number;
  raw?: any;
  [key: string]: any;
}

const PAGE_SIZE_OPTIONS = [25, 50, 100];

const fixed = (digits: number) => (params: any) =>
  typeof params.value === "number" ? params.value.toFixed(digits) : "—";

// ML scores fritz's alerts page carried as their own columns. Rendered only
// when at least one row has the score, so non-ZTF brokers don't get empty
// columns.
const ML_SCORE_FIELDS = [
  "drb",
  "braai",
  "acai_h",
  "acai_n",
  "acai_o",
  "acai_v",
  "acai_b",
  "btsbot",
];

interface BrokerAlertTableProps {
  rows: AlertRow[];
  onRowClick: (row: AlertRow) => void;
  // A cone search was run, so the separation column is meaningful.
  hasPosition: boolean;
  // Bumped per search, to re-apply the default sort for the new results.
  searchKey: number;
}

/**
 * One row per alert, with the column set from fritz's alerts page. Clicking a
 * row opens its detail dialog; column picking, filtering and CSV export come
 * from the shared grid toolbar.
 */
const BrokerAlertTable = ({
  rows,
  onRowClick,
  hasPosition,
  searchKey,
}: BrokerAlertTableProps) => {
  const present = (field: string) =>
    rows.some((r) => typeof r[field] === "number");
  // Non-numeric columns (candid, band, isdiffpos): several providers normalize
  // them away entirely, and an all-"—" column is just noise.
  const has = (field: string) =>
    rows.some((r) => r[field] !== undefined && r[field] !== null);

  // Nearest first for a cone search, newest first otherwise. Sorting is
  // controlled rather than initial state so a new search re-applies it; column
  // visibility and page size stay as the user left them.
  const defaultSort = () => [
    hasPosition && present("separation")
      ? { field: "separation", sort: "asc" }
      : { field: "jd", sort: "desc" },
  ];
  const [sortModel, setSortModel] = useState<any[]>(defaultSort);
  useEffect(() => {
    setSortModel(defaultSort());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchKey]);

  const columns: any[] = [
    { field: "objectId", headerName: "objectId", flex: 1.2, minWidth: 140 },
    ...(has("candid")
      ? [{ field: "candid", headerName: "candid", flex: 1.2, minWidth: 150 }]
      : []),
    {
      field: "jd",
      headerName: "jd",
      flex: 1,
      minWidth: 120,
      filterable: false,
      sortingOrder: ["desc", "asc", null],
      renderCell: fixed(5),
    },
    ...(hasPosition && present("separation")
      ? [
          {
            field: "separation",
            headerName: 'sep ["]',
            flex: 0.8,
            minWidth: 90,
            filterable: false,
            renderCell: (params: any) =>
              typeof params.value === "number"
                ? `${params.value.toFixed(2)}"`
                : "—",
          },
        ]
      : []),
    {
      field: "ra",
      headerName: "ra",
      flex: 1,
      minWidth: 110,
      filterable: false,
      renderCell: fixed(6),
    },
    {
      field: "dec",
      headerName: "dec",
      flex: 1,
      minWidth: 110,
      filterable: false,
      renderCell: fixed(6),
    },
    ...(has("band")
      ? [{ field: "band", headerName: "band", flex: 0.6, minWidth: 80 }]
      : []),
    {
      field: "magpsf",
      headerName: "magpsf",
      flex: 1,
      minWidth: 130,
      filterable: false,
      // sigmapsf folds into this cell rather than taking its own column.
      renderCell: (params: any) => {
        const { magpsf, sigmapsf } = params.row;
        if (typeof magpsf !== "number") return "—";
        return typeof sigmapsf === "number"
          ? `${magpsf.toFixed(3)} ± ${sigmapsf.toFixed(3)}`
          : magpsf.toFixed(3);
      },
    },
    ...(present("snr")
      ? [
          {
            field: "snr",
            headerName: "snr",
            flex: 0.7,
            minWidth: 80,
            filterable: false,
            renderCell: fixed(2),
          },
        ]
      : []),
    ...(has("isdiffpos")
      ? [
          {
            field: "isdiffpos",
            headerName: "isdiffpos",
            flex: 0.7,
            minWidth: 90,
            renderCell: (params: any) =>
              params.value != null ? String(params.value) : "—",
          },
        ]
      : []),
    ...ML_SCORE_FIELDS.filter(present).map((field) => ({
      field,
      headerName: field,
      flex: 0.8,
      minWidth: 90,
      filterable: false,
      renderCell: fixed(3),
    })),
    ...(present("programid")
      ? [
          {
            field: "programid",
            headerName: "programid",
            flex: 0.7,
            minWidth: 90,
          },
        ]
      : []),
  ];

  return (
    <StyledDataGrid
      autoHeight
      rows={rows}
      columns={columns}
      getRowId={(row: AlertRow) => row.id}
      onRowClick={(params: any) => onRowClick(params.row)}
      pageSizeOptions={PAGE_SIZE_OPTIONS}
      sortModel={sortModel}
      onSortModelChange={setSortModel}
      initialState={{
        pagination: { paginationModel: { pageSize: 25, page: 0 } },
      }}
      sx={{ "& .MuiDataGrid-row": { cursor: "pointer" } }}
      slots={{ toolbar: DataGridToolbar }}
      slotProps={{ toolbar: { showFilter: true } }}
      showToolbar
    />
  );
};

export default BrokerAlertTable;

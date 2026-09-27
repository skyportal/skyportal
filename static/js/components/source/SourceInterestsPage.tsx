import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import MuiLink from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import WorkspacesIcon from "@mui/icons-material/Workspaces";
import { GridColDef, GridSortModel, ToolbarButton } from "@mui/x-data-grid";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import {
  SourceInterest,
  useGetAllSourceInterestsQuery,
} from "../../ducks/sourceInterests";

dayjs.extend(utc);

type SourceInterestRow = SourceInterest & { interest_count: number };

const COLUMNS: GridColDef<SourceInterestRow>[] = [
  {
    field: "obj_id",
    headerName: "Source",
    flex: 1,
    minWidth: 130,
    sortable: false,
    renderCell: ({ row }) => (
      <Link to={`/source/${row.obj_id}`}>{row.obj_id}</Link>
    ),
  },
  {
    field: "interest_count",
    headerName: "Interests",
    type: "number",
    width: 100,
    align: "center",
    headerAlign: "center",
    rowSpanValueGetter: (_value, row) => row.obj_id,
    renderCell: ({ value }) => (
      <Chip
        size="small"
        label={value}
        sx={{
          fontWeight: 600,
          color: "white",
          bgcolor: `hsl(${50 - (50 * Math.min(value - 1, 6)) / 6}, 90%, 45%)`,
        }}
      />
    ),
    sortComparator: (v1, v2, p1, p2) =>
      v1 - v2 ||
      p1.api.getRow(p1.id).obj_id.localeCompare(p2.api.getRow(p2.id).obj_id),
  },
  {
    field: "title",
    headerName: "Title",
    flex: 3,
    minWidth: 250,
    sortable: false,
    valueGetter: (_value, row) => `${row.title} ${row.description ?? ""}`,
    rowSpanValueGetter: () => null,
    renderCell: ({ row }) => (
      <Stack>
        <Typography variant="subtitle2">{row.title}</Typography>
        {row.description && (
          <Typography variant="body2" color="textSecondary">
            {row.description}
          </Typography>
        )}
      </Stack>
    ),
  },
  {
    field: "link",
    headerName: "Link",
    flex: 1,
    minWidth: 140,
    sortable: false,
    rowSpanValueGetter: () => null,
    renderCell: ({ row }) =>
      row.link && (
        <MuiLink href={row.link} target="_blank" rel="noreferrer">
          {row.link}
        </MuiLink>
      ),
  },
  {
    field: "user",
    headerName: "User",
    flex: 1,
    minWidth: 130,
    sortable: false,
    valueGetter: (_value, row) => row.user.username,
    rowSpanValueGetter: () => null,
    renderCell: ({ row }) => (
      <Chip
        size="small"
        label={row.user.username}
        component={Link}
        to={`/user/${row.user.id}`}
        clickable
      />
    ),
  },
  {
    field: "created_at",
    headerName: "Registered",
    flex: 1,
    minWidth: 150,
    valueGetter: (value) => dayjs.utc(value).format("YYYY-MM-DD HH:mm"),
    rowSpanValueGetter: () => null,
  },
];

const SourceInterestsPage = () => {
  const { data: interests } = useGetAllSourceInterestsQuery();
  const [grouped, setGrouped] = useState(false);
  const [sortModel, setSortModel] = useState<GridSortModel>([]);

  const rows = useMemo(() => {
    const counts: Record<string, number> = {};
    interests?.forEach(({ obj_id }) => {
      counts[obj_id] = (counts[obj_id] ?? 0) + 1;
    });
    return (interests ?? []).map((interest) => ({
      ...interest,
      interest_count: counts[interest.obj_id],
    }));
  }, [interests]);

  return (
    <StyledDataGrid
      loading={!interests}
      rows={rows}
      columns={COLUMNS}
      getRowHeight={() => "auto"}
      rowSpanning={grouped}
      sortModel={sortModel}
      onSortModelChange={setSortModel}
      sx={{
        height: "calc(100vh - 5.25rem)",
        "& .MuiDataGrid-cell": {
          whiteSpace: "normal",
          display: "flex",
          alignItems: "center",
        },
        "& .MuiDataGrid-row > [role='none']": { flexShrink: 0 },
      }}
      pageSizeOptions={[25, 50, 100]}
      initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
      slots={{ toolbar: DataGridToolbar }}
      slotProps={{
        toolbar: {
          title: "Source interests",
          showColumns: false,
          showExport: false,
          children: (
            <Tooltip title={grouped ? "Ungroup" : "Group by source"}>
              <ToolbarButton
                aria-label="Group by source"
                color={grouped ? "primary" : "default"}
                onClick={() => {
                  setGrouped(!grouped);
                  if (!grouped) {
                    setSortModel([{ field: "interest_count", sort: "desc" }]);
                  }
                }}
              >
                <WorkspacesIcon fontSize="small" />
              </ToolbarButton>
            </Tooltip>
          ),
        },
      }}
      showToolbar
    />
  );
};

export default SourceInterestsPage;

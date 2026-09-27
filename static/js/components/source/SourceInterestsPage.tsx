import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import MuiLink from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { GridColDef } from "@mui/x-data-grid";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import {
  SourceInterest,
  useGetAllSourceInterestsQuery,
} from "../../ducks/sourceInterests";

dayjs.extend(utc);

const COLUMNS: GridColDef<SourceInterest>[] = [
  {
    field: "obj_id",
    headerName: "Source",
    flex: 1,
    minWidth: 130,
    renderCell: ({ row }) => (
      <Link to={`/source/${row.obj_id}`}>{row.obj_id}</Link>
    ),
  },
  {
    field: "title",
    headerName: "Title",
    flex: 3,
    minWidth: 250,
    valueGetter: (_value, row) => `${row.title} ${row.description ?? ""}`,
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
    valueGetter: (_value, row) => row.user.username,
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
  },
];

const SourceInterestsPage = () => {
  const { data: interests } = useGetAllSourceInterestsQuery();

  return (
    <StyledDataGrid
      loading={!interests}
      rows={interests ?? []}
      columns={COLUMNS}
      getRowHeight={() => "auto"}
      sx={{
        height: "calc(100vh - 5.25rem)",
        "& .MuiDataGrid-cell": { whiteSpace: "normal" },
      }}
      pageSizeOptions={[25, 50, 100]}
      initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
      slots={{ toolbar: DataGridToolbar }}
      slotProps={{
        toolbar: {
          title: "Source interests",
          showColumns: false,
          showExport: false,
        },
      }}
      showToolbar
    />
  );
};

export default SourceInterestsPage;

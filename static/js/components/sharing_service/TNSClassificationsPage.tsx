import { useState } from "react";
import { Link } from "react-router-dom";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import Button from "../Button";
import StyledDataGridBase, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT_WITH_TABS,
} from "../StyledDataGrid";
import SharingServicesDialog from "./SharingServicesForm";
import { emptyCell, renderStatus } from "./SharingServiceSubmissionsPage";
import { useGetTNSClassificationsQuery } from "../../ducks/sharingServices";
import { useGetUsersQuery } from "../../ducks/users";
import { userLabel } from "../../utils/format";

dayjs.extend(utc);

const StyledDataGrid: any = StyledDataGridBase;

const PERIODS = [7, 30, 90, 365];

const REASON_SEVERITY: Record<string, string | null> = {
  queued: "info",
  held: "warning",
  failed: "error",
  no_tns_name: "warning",
  no_spectrum: "warning",
  no_tns_type: "warning",
  missing_credits: "warning",
  manual: null,
};

const REPORTABLE = ["failed", "missing_credits", "manual"];

const localTime = (date: string) =>
  dayjs.utc(date).local().format("YYYY-MM-DD HH:mm");

const waitingFor = (date: string) => {
  const hours = dayjs().diff(dayjs.utc(date), "hour");
  if (hours < 1) return "< 1 h";
  return hours < 48 ? `${hours} h` : `${Math.floor(hours / 24)} days`;
};

const tnsObjectUrl = (tnsName: string) =>
  `https://www.wis-tns.org/object/${tnsName.trim().split(" ").pop()}`;

const renderSource = ({ row }: any) => (
  <Box sx={{ display: "flex", flexDirection: "column" }}>
    <Link to={`/source/${row.obj_id}`} style={{ whiteSpace: "nowrap" }}>
      {row.obj_id}
    </Link>
    {row.tns_name && (
      <Typography
        component="a"
        variant="caption"
        href={tnsObjectUrl(row.tns_name)}
        target="_blank"
        rel="noopener noreferrer"
        sx={{ color: "text.secondary", whiteSpace: "nowrap" }}
      >
        {row.tns_name}
      </Typography>
    )}
  </Box>
);

const renderRedshift = ({ row }: any) =>
  row.redshift === null || row.redshift === undefined
    ? emptyCell
    : Number(row.redshift).toFixed(4);

const renderReason = ({ row }: any) => {
  const severity = REASON_SEVERITY[row.reason_code];
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
      <Box
        sx={(theme: any) => {
          const shade = theme.palette.mode === "dark" ? "light" : "dark";
          const base = severity ? theme.palette[severity][shade] : null;
          return {
            width: "fit-content",
            maxWidth: "100%",
            px: 1,
            py: 0.25,
            borderRadius: 1.5,
            fontSize: "0.8125rem",
            fontWeight: 500,
            overflowWrap: "anywhere",
            color: base || theme.palette.text.secondary,
            backgroundColor: base
              ? alpha(base, 0.12)
              : theme.palette.action.selected,
          };
        }}
      >
        {row.reason}
      </Box>
      {row.tns_send_after && (
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          Sends {localTime(row.tns_send_after)}
        </Typography>
      )}
    </Box>
  );
};

interface ToolbarProps {
  days: number;
  setDays: (days: number) => void;
}

const TNSClassificationsToolbar = ({ days, setDays }: ToolbarProps) => (
  <DataGridToolbar title="TNS classifications">
    <TextField
      select
      size="small"
      value={days}
      onChange={(e) => setDays(Number(e.target.value))}
      sx={{ minWidth: 140 }}
    >
      {PERIODS.map((period) => (
        <MenuItem key={period} value={period}>
          Last {period} days
        </MenuItem>
      ))}
    </TextField>
  </DataGridToolbar>
);

const TNSClassificationsPage = () => {
  const [days, setDays] = useState(30);
  const [tab, setTab] = useState("not_reported");
  const [reportObjId, setReportObjId] = useState<string | null>(null);
  const { data, isFetching } = useGetTNSClassificationsQuery({ days });
  const users = useGetUsersQuery().data?.users ?? [];
  const usersById = Object.fromEntries(
    users.map((user: any) => [user.id, user]),
  );

  const notReported = data?.not_reported ?? [];
  const reported = data?.reported ?? [];

  const notReportedColumns = [
    {
      field: "obj_id",
      headerName: "Source",
      flex: 0.8,
      minWidth: 130,
      renderCell: renderSource,
    },
    {
      field: "classification",
      headerName: "Classification",
      flex: 0.9,
      minWidth: 140,
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", flexDirection: "column" }}>
          <Typography variant="body2">{row.classification}</Typography>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {row.classified_by}
          </Typography>
        </Box>
      ),
    },
    {
      field: "classified_at",
      headerName: "Waiting for",
      flex: 0.6,
      minWidth: 100,
      renderCell: ({ row }: any) => (
        <Tooltip title={`Classified ${localTime(row.classified_at)}`}>
          <span>{waitingFor(row.classified_at)}</span>
        </Tooltip>
      ),
    },
    {
      field: "instrument",
      headerName: "Spectrum",
      flex: 0.6,
      minWidth: 100,
      renderCell: ({ row }: any) => row.instrument ?? emptyCell,
    },
    {
      field: "redshift",
      headerName: "Redshift",
      flex: 0.5,
      minWidth: 90,
      renderCell: renderRedshift,
    },
    {
      field: "tns_classification",
      headerName: "On TNS",
      flex: 0.6,
      minWidth: 100,
      renderCell: ({ row }: any) => row.tns_classification ?? emptyCell,
    },
    {
      field: "reason",
      headerName: "Reason",
      flex: 1.6,
      minWidth: 220,
      renderCell: renderReason,
    },
    {
      field: "report",
      headerName: "",
      width: 110,
      sortable: false,
      filterable: false,
      disableExport: true,
      renderCell: ({ row }: any) =>
        REPORTABLE.includes(row.reason_code) ? (
          <Button
            size="small"
            variant="outlined"
            onClick={() => setReportObjId(row.obj_id)}
          >
            Report
          </Button>
        ) : null,
    },
  ];

  const reportedColumns = [
    {
      field: "created_at",
      headerName: "Sent",
      flex: 0.7,
      minWidth: 140,
      renderCell: ({ row }: any) => localTime(row.created_at),
    },
    {
      field: "obj_id",
      headerName: "Source",
      flex: 0.8,
      minWidth: 130,
      renderCell: renderSource,
    },
    {
      field: "classification",
      headerName: "Classification",
      flex: 0.7,
      minWidth: 120,
      renderCell: ({ row }: any) => row.classification ?? emptyCell,
    },
    {
      field: "redshift",
      headerName: "Redshift",
      flex: 0.5,
      minWidth: 90,
      renderCell: renderRedshift,
    },
    {
      field: "instrument",
      headerName: "Instrument",
      flex: 0.6,
      minWidth: 100,
      renderCell: ({ row }: any) => row.instrument ?? emptyCell,
    },
    {
      field: "authors",
      headerName: "Authors",
      flex: 2.2,
      minWidth: 260,
      renderCell: ({ row }: any) => (
        <Typography variant="body2" sx={{ fontSize: "0.8rem" }}>
          {row.authors}
        </Typography>
      ),
    },
    {
      field: "auto_submission",
      headerName: "Mode",
      flex: 0.5,
      minWidth: 100,
      valueGetter: (value: boolean) => (value ? "Automatic" : "Manual"),
    },
    {
      field: "user_id",
      headerName: "By",
      flex: 0.7,
      minWidth: 120,
      valueGetter: (value: number) => userLabel(usersById[value], false, true),
    },
    {
      field: "tns_status",
      headerName: "Status",
      flex: 0.8,
      minWidth: 120,
      renderCell: ({ row }: any) => renderStatus(row.tns_status),
    },
    {
      field: "sharing_service",
      headerName: "Service",
      flex: 0.6,
      minWidth: 100,
    },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Tabs value={tab} onChange={(_, value) => setTab(value)}>
        <Tab
          value="not_reported"
          label={`Not reported (${notReported.length})`}
        />
        <Tab value="reported" label={`Reported (${reported.length})`} />
      </Tabs>
      <StyledDataGrid
        height={FULL_PAGE_HEIGHT_WITH_TABS}
        loading={isFetching}
        rows={tab === "reported" ? reported : notReported}
        columns={tab === "reported" ? reportedColumns : notReportedColumns}
        getRowId={(row: any) =>
          tab === "reported" ? row.id : row.classification_id
        }
        getRowHeight={() => "auto"}
        sx={{
          "& .MuiDataGrid-cell": {
            whiteSpace: "normal",
            alignItems: "center",
            py: 1,
          },
        }}
        initialState={{
          columns: { columnVisibilityModel: { sharing_service: false } },
        }}
        slots={{ toolbar: TNSClassificationsToolbar }}
        slotProps={{ toolbar: { days, setDays } }}
        showToolbar
      />
      {reportObjId && (
        <SharingServicesDialog
          obj_id={reportObjId}
          dialogOpen
          setDialogOpen={(open: boolean) => !open && setReportObjId(null)}
        />
      )}
    </Box>
  );
};

export default TNSClassificationsPage;

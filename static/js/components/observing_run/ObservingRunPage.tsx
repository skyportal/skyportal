import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery, useIsReadOnly } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useDeleteObservingRunMutation } from "../../ducks/observingRun";
import { useGetObservingRunsQuery } from "../../ducks/observingRuns";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { observingRunTitle } from "./AssignmentForm";
import NewObservingRun from "./NewObservingRun";
import ModifyObservingRun from "./ModifyObservingRun";

dayjs.extend(utc);
dayjs.extend(duration);
dayjs.extend(relativeTime);

interface RunsToolbarProps {
  displayAll: boolean;
  setDisplayAll: (displayAll: boolean) => void;
}

const RunsToolbar = ({ displayAll, setDisplayAll }: RunsToolbarProps) => (
  <DataGridToolbar title="Observing Runs" showExport={false}>
    <ToggleButtonGroup
      size="small"
      value={displayAll}
      exclusive
      onChange={(_e, value) => value !== null && setDisplayAll(value)}
    >
      <ToggleButton value={false}>Upcoming runs</ToggleButton>
      <ToggleButton value={true}>All runs</ToggleButton>
    </ToggleButtonGroup>
  </DataGridToolbar>
);

const isUpcoming = (run: any) => {
  const msUntilEnd = dayjs(run.calendar_date)
    .add(run.duration - 1, "day")
    .diff(dayjs().utc().subtract(1.5, "day"));
  return (
    msUntilEnd > 0 && msUntilEnd < dayjs.duration(1, "month").asMilliseconds()
  );
};

const ObservingRunPage = () => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const permissions = useGetProfileQuery().data?.permissions;
  const managePermission =
    permissions?.includes("System admin") ||
    permissions?.includes("Manage observing runs");
  const { data: observingRuns = [] } = useGetObservingRunsQuery();
  const { data: instruments = [] } = useGetInstrumentsQuery();
  const { data: telescopes = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all ?? [];
  const [deleteObservingRun] = useDeleteObservingRunMutation();
  const [runToEdit, setRunToEdit] = useState<number | null>(null);
  const [runToDelete, setRunToDelete] = useState<number | null>(null);
  const [displayAll, setDisplayAll] = useState(false);

  const rows = displayAll
    ? [...observingRuns].sort((a, b) =>
        dayjs(b.calendar_date).diff(dayjs(a.calendar_date)),
      )
    : observingRuns.filter(isUpcoming);

  const deleteRun = async () => {
    try {
      await deleteObservingRun(runToDelete!).unwrap();
      dispatch(showNotification("Observing run deleted"));
      setRunToDelete(null);
    } catch {
      // error notification handled by the base query
    }
  };

  const columns: any[] = [
    {
      field: "title",
      headerName: "Run",
      flex: 3,
      minWidth: 300,
      valueGetter: (_value: any, run: any) =>
        observingRunTitle(run, instruments, telescopes, groups),
      renderCell: ({ row, value }: any) => (
        <Link component={RouterLink} to={`/run/${row.id}`} underline="hover">
          {value}
        </Link>
      ),
    },
    {
      field: "calendar_date",
      headerName: "Starts",
      flex: 1,
      minWidth: 120,
      valueFormatter: (value: string) =>
        dayjs.duration(dayjs(value).diff(dayjs().utc())).humanize(true),
    },
    { field: "observers", headerName: "Observers", flex: 1, minWidth: 120 },
    { field: "duration", headerName: "Nights", minWidth: 80 },
    ...(managePermission
      ? [
          {
            field: "actions",
            headerName: "",
            sortable: false,
            filterable: false,
            minWidth: 100,
            renderCell: ({ row }: any) => (
              <Box sx={{ display: "flex" }}>
                <IconButton onClick={() => setRunToEdit(row.id)}>
                  <EditIcon />
                </IconButton>
                <IconButton
                  color="error"
                  onClick={() => setRunToDelete(row.id)}
                >
                  <DeleteIcon />
                </IconButton>
              </Box>
            ),
          },
        ]
      : []),
  ];

  return (
    <Grid container spacing={3}>
      <Grid size={{ lg: 8, sm: 12 }}>
        <StyledDataGrid
          autoHeight
          rows={rows}
          columns={columns}
          initialState={{ pagination: { paginationModel: { pageSize: 100 } } }}
          pageSizeOptions={[25, 50, 100]}
          localeText={{ noRowsLabel: "No observing runs to show." }}
          slots={{ toolbar: RunsToolbar }}
          slotProps={{ toolbar: { displayAll, setDisplayAll } }}
          showToolbar
        />
      </Grid>
      {!isReadOnly && (
        <Grid size={{ lg: 4, sm: 12 }}>
          <NewObservingRun />
        </Grid>
      )}
      <Dialog open={runToEdit !== null} onClose={() => setRunToEdit(null)}>
        <DialogTitle>Edit Observing Run</DialogTitle>
        <DialogContent dividers>
          <ModifyObservingRun
            run_id={runToEdit}
            onClose={() => setRunToEdit(null)}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteRun}
        dialogOpen={runToDelete !== null}
        closeDialog={() => setRunToDelete(null)}
        resourceName="observing run"
      />
    </Grid>
  );
};

export default ObservingRunPage;

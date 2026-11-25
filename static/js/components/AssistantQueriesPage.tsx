import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useAppDispatch } from "../types/hooks";
import { useGetGroupsQuery } from "../ducks/groups";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";
import SearchableValueSelect from "./SearchableValueSelect";
import StyledDataGrid, { DataGridToolbar } from "./StyledDataGrid";
import { type AssistantQuery } from "../ducks/assistant_queries";
import {
  useCreateAssistantQueryMutation,
  useDeleteAssistantQueryMutation,
  useGetAssistantQueriesQuery,
  useGetAssistantQueryRunsQuery,
  useRunAssistantQueryMutation,
  useSubscribeAssistantQueryMutation,
  useUnsubscribeAssistantQueryMutation,
  useUpdateAssistantQueryMutation,
} from "../ducks/assistant_queries";

const useStyles = makeStyles()(() => ({
  paperContent: { padding: "1rem" },
  form: { minWidth: "24rem", paddingTop: "0.5rem" },
}));

const emptyForm = {
  name: "",
  prompt: "",
  group_id: "",
  analysis_service_match: "",
  context_type: "source",
  source_id: "",
  interval_minutes: "",
  active: true,
  description: "",
  dry_run: false,
};

const utcLabel = (value: string) => {
  const date = new Date(
    /(Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`,
  );
  return date.toLocaleString(undefined, {
    timeZone: "UTC",
    timeZoneName: "short",
  });
};

const AssistantQueriesPage = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const { data: queries } = useGetAssistantQueriesQuery(undefined, {
    pollingInterval: 30000,
  });
  const userGroups = useGetGroupsQuery().data?.user ?? [];

  const [createQuery] = useCreateAssistantQueryMutation();
  const [updateQuery] = useUpdateAssistantQueryMutation();
  const [deleteQuery] = useDeleteAssistantQueryMutation();
  const [runQuery, { isLoading: running }] = useRunAssistantQueryMutation();
  const [subscribe] = useSubscribeAssistantQueryMutation();
  const [unsubscribe] = useUnsubscribeAssistantQueryMutation();

  const [openForm, setOpenForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<any>(emptyForm);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [queryToDelete, setQueryToDelete] = useState<number | null>(null);
  const [historyQuery, setHistoryQuery] = useState<AssistantQuery | null>(null);
  const {
    data: runs,
    isFetching: fetchingRuns,
    isError: runsError,
  } = useGetAssistantQueryRunsQuery(historyQuery?.id ?? 0, {
    skip: historyQuery == null,
    pollingInterval: 5000,
  });

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setOpenForm(true);
  };

  const openEdit = (row: any) => {
    setEditId(row.id);
    setForm({
      name: row.name ?? "",
      prompt: row.prompt ?? "",
      group_id: row.group_id,
      analysis_service_match: row.analysis_service_match ?? "",
      context_type: row.context_type,
      source_id: row.source_id ?? "",
      interval_minutes: row.interval_minutes?.toString() ?? "",
      active: row.active,
      description: row.description ?? "",
      dry_run: row.dry_run ?? false,
    });
    setOpenForm(true);
  };

  const toggleSubscription = async (row: any) => {
    try {
      if (row.subscribed) {
        await unsubscribe(row.id).unwrap();
      } else {
        await subscribe(row.id).unwrap();
      }
    } catch {
      // error notification handled by the base query
    }
  };

  const submitForm = async () => {
    if (!form.name || !form.prompt || !form.group_id) {
      dispatch(
        showNotification("Name, group and prompt are required", "error"),
      );
      return;
    }
    const interval =
      form.interval_minutes === "" ? null : Number(form.interval_minutes);
    if (
      interval != null &&
      (!Number.isInteger(interval) || interval < 1 || interval > 10080)
    ) {
      dispatch(
        showNotification("Enter an interval from 1 to 10,080 minutes", "error"),
      );
      return;
    }
    const sourceMode = form.context_type === "source";
    if (sourceMode && interval != null && !form.source_id.trim()) {
      dispatch(showNotification("Select a source for interval runs", "error"));
      return;
    }
    const body = {
      name: form.name,
      prompt: form.prompt,
      description: form.description || null,
      analysis_service_match: sourceMode
        ? form.analysis_service_match || null
        : null,
      context_type: form.context_type,
      source_id: sourceMode ? form.source_id.trim() || null : null,
      interval_minutes: interval,
      active: form.active,
      dry_run: form.dry_run,
    };
    try {
      if (editId != null) {
        await updateQuery({ id: editId, body }).unwrap();
        dispatch(showNotification("Assistant query updated"));
      } else {
        await createQuery({ ...body, group_id: form.group_id }).unwrap();
        dispatch(showNotification("Assistant query created"));
      }
      setForm(emptyForm);
      setEditId(null);
      setOpenForm(false);
    } catch {
      // error notification handled by the base query
    }
  };

  const runNow = async (query: AssistantQuery) => {
    try {
      const { queued, failed } = await runQuery(query.id).unwrap();
      setHistoryQuery(query);
      if (failed) {
        dispatch(
          showNotification(
            `Queued ${queued}. Could not dispatch ${failed}.`,
            "error",
          ),
        );
      } else {
        dispatch(
          showNotification(
            queued ? `Queued ${queued} review(s)` : "No new reviews to queue",
          ),
        );
      }
    } catch {
      // error notification handled by the base query
    }
  };

  const doDelete = async () => {
    if (queryToDelete == null) return;
    try {
      await deleteQuery(queryToDelete).unwrap();
      dispatch(showNotification("Assistant query deleted"));
    } catch {
      // error notification handled by the base query
    }
    setDialogOpen(false);
    setQueryToDelete(null);
  };

  if (!queries) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const columns: any[] = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 140 },
    {
      field: "description",
      headerName: "Description",
      flex: 1.5,
      minWidth: 180,
    },
    { field: "group_name", headerName: "Group", flex: 1, minWidth: 120 },
    {
      field: "analysis_service_match",
      headerName: "Triggered by",
      flex: 1,
      minWidth: 120,
      valueGetter: (_v: any, row: any) => row.analysis_service_match || "—",
    },
    {
      field: "interval_minutes",
      headerName: "Interval",
      width: 110,
      valueFormatter: (value: number | null) =>
        value == null ? "—" : `${value} min`,
    },
    {
      field: "next_run_at",
      headerName: "Next check",
      minWidth: 170,
      valueFormatter: (value: string | null) => (value ? utcLabel(value) : "—"),
    },
    {
      field: "last_run_at",
      headerName: "Last check",
      minWidth: 230,
      valueGetter: (value: string | null, row: AssistantQuery) =>
        value
          ? `${utcLabel(value)} · ${row.last_run_count == null ? "Could not queue" : `${row.last_run_count} queued`}`
          : "—",
    },
    {
      field: "task_actions",
      headerName: "Runs",
      width: 165,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: { row: AssistantQuery }) =>
        row.is_owner ? (
          <>
            <Button
              size="small"
              disabled={
                running || (row.context_type === "source" && !row.source_id)
              }
              onClick={() => runNow(row)}
            >
              Run now
            </Button>
            <Button size="small" onClick={() => setHistoryQuery(row)}>
              History
            </Button>
          </>
        ) : null,
    },
    { field: "subscriber_count", headerName: "Subscribers", width: 110 },
    {
      field: "subscribed",
      headerName: " ",
      width: 130,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => (
        <Button
          size="small"
          variant={params.row.subscribed ? "outlined" : "contained"}
          onClick={() => toggleSubscription(params.row)}
        >
          {params.row.subscribed ? "Unsubscribe" : "Notify me"}
        </Button>
      ),
    },
    {
      field: "edit",
      headerName: " ",
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: (params: any) =>
        params.row.is_owner ? (
          <IconButton onClick={() => openEdit(params.row)}>
            <EditIcon />
          </IconButton>
        ) : null,
    },
    {
      field: "delete",
      headerName: " ",
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: (params: any) =>
        params.row.is_owner ? (
          <IconButton
            onClick={() => {
              setQueryToDelete(params.row.id);
              setDialogOpen(true);
            }}
          >
            <DeleteIcon />
          </IconButton>
        ) : null,
    },
  ];

  const CustomToolbar = () => (
    <DataGridToolbar showQuickFilter>
      <IconButton name="new_assistant_query_form" onClick={openCreate}>
        <AddIcon />
      </IconButton>
    </DataGridToolbar>
  );

  return (
    <div className={classes.paperContent}>
      <Typography variant="h6">Assistant queries</Typography>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        Automated assistant runs shared within a group. Subscribe to be notified
        with the result, or add one for your group.
      </Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={queries}
          columns={columns}
          getRowId={(row: any) => row.id}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Box>

      <Dialog open={openForm} onClose={() => setOpenForm(false)}>
        <DialogTitle>
          {editId != null ? "Edit assistant query" : "Add an assistant query"}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} className={classes.form}>
            <TextField
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <TextField
              label="Description"
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
            <SearchableValueSelect
              label="Group"
              options={userGroups}
              value={form.group_id === "" ? null : form.group_id}
              onChange={(id) => setForm({ ...form, group_id: id ?? "" })}
              required
              disabled={editId != null}
              {...(editId != null && {
                helperText: "A query's group can't be changed.",
              })}
            />
            <TextField
              select
              label="Review scope"
              value={form.context_type}
              onChange={(e) =>
                setForm({ ...form, context_type: e.target.value })
              }
            >
              <MenuItem value="source">Source</MenuItem>
              <MenuItem value="gcn_event">Recent GRBs</MenuItem>
            </TextField>
            {form.context_type === "source" && (
              <>
                <TextField
                  label="Triggered by analysis service (name contains)"
                  value={form.analysis_service_match}
                  onChange={(e) =>
                    setForm({ ...form, analysis_service_match: e.target.value })
                  }
                  placeholder="e.g. flare, oracle"
                />
                <TextField
                  label="Source ID for interval and manual runs"
                  value={form.source_id}
                  onChange={(e) =>
                    setForm({ ...form, source_id: e.target.value })
                  }
                  helperText="Use a source saved to this group."
                />
              </>
            )}
            <TextField
              label="Interval (minutes)"
              type="number"
              value={form.interval_minutes}
              onChange={(e) =>
                setForm({ ...form, interval_minutes: e.target.value })
              }
              helperText="Leave blank to turn off interval runs."
              slotProps={{ htmlInput: { min: 1, max: 10080, step: 1 } }}
            />
            <TextField
              label="Prompt"
              value={form.prompt}
              onChange={(e) => setForm({ ...form, prompt: e.target.value })}
              multiline
              minRows={3}
              required
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={form.dry_run}
                  onChange={(e) =>
                    setForm({ ...form, dry_run: e.target.checked })
                  }
                />
              }
              label="Dry run (preview only)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={form.active}
                  onChange={(e) =>
                    setForm({ ...form, active: e.target.checked })
                  }
                />
              }
              label="Enable automatic runs"
            />
            <Button variant="contained" onClick={submitForm}>
              {editId != null ? "Save" : "Create"}
            </Button>
          </Stack>
        </DialogContent>
      </Dialog>

      <Dialog
        open={historyQuery != null}
        onClose={() => setHistoryQuery(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{historyQuery?.name} run history</DialogTitle>
        <DialogContent>
          {runsError && (
            <Typography>Run history could not be loaded.</Typography>
          )}
          {fetchingRuns && !runs && <CircularProgress size={24} />}
          {runs?.length === 0 && (
            <Typography>No reviews queued yet.</Typography>
          )}
          <Stack spacing={2}>
            {runs?.map((run) => (
              <Box key={run.id}>
                <Typography variant="subtitle2">
                  {run.context_id} · {run.run_status} ·{" "}
                  {utcLabel(run.created_at)}
                </Typography>
                {run.result && (
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                    {run.result}
                  </Typography>
                )}
              </Box>
            ))}
          </Stack>
        </DialogContent>
      </Dialog>

      <ConfirmDeletionDialog
        deleteFunction={doDelete}
        dialogOpen={dialogOpen}
        closeDialog={() => setDialogOpen(false)}
        resourceName="assistant query"
      />
    </div>
  );
};

export default AssistantQueriesPage;

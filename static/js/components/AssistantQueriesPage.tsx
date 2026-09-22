import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
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
import StyledDataGrid, { DataGridToolbar } from "./StyledDataGrid";
import {
  useCreateAssistantQueryMutation,
  useDeleteAssistantQueryMutation,
  useGetAssistantQueriesQuery,
  useSubscribeAssistantQueryMutation,
  useUnsubscribeAssistantQueryMutation,
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
  description: "",
  dry_run: false,
};

const AssistantQueriesPage = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  const { data: queries } = useGetAssistantQueriesQuery();
  const userGroups = useGetGroupsQuery().data?.user ?? [];

  const [createQuery] = useCreateAssistantQueryMutation();
  const [deleteQuery] = useDeleteAssistantQueryMutation();
  const [subscribe] = useSubscribeAssistantQueryMutation();
  const [unsubscribe] = useUnsubscribeAssistantQueryMutation();

  const [openNewForm, setOpenNewForm] = useState(false);
  const [form, setForm] = useState<any>(emptyForm);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [queryToDelete, setQueryToDelete] = useState<number | null>(null);

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

  const submitNew = async () => {
    if (!form.name || !form.prompt || !form.group_id) {
      dispatch(
        showNotification("Name, group and prompt are required", "error"),
      );
      return;
    }
    try {
      await createQuery({
        name: form.name,
        prompt: form.prompt,
        group_id: form.group_id,
        description: form.description || null,
        analysis_service_match: form.analysis_service_match || null,
        dry_run: form.dry_run,
      }).unwrap();
      dispatch(showNotification("Assistant query created"));
      setForm(emptyForm);
      setOpenNewForm(false);
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
      <IconButton
        name="new_assistant_query_form"
        onClick={() => setOpenNewForm(true)}
      >
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

      <Dialog open={openNewForm} onClose={() => setOpenNewForm(false)}>
        <DialogTitle>Add an assistant query</DialogTitle>
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
            <TextField
              select
              label="Group"
              value={form.group_id}
              onChange={(e) => setForm({ ...form, group_id: e.target.value })}
              required
            >
              {userGroups.map((g: any) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Triggered by analysis service (name contains)"
              value={form.analysis_service_match}
              onChange={(e) =>
                setForm({ ...form, analysis_service_match: e.target.value })
              }
              placeholder="e.g. flare, oracle"
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
              label="Dry run (run but notify no one)"
            />
            <Button variant="contained" onClick={submitNew}>
              Create
            </Button>
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

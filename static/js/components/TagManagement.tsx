import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogActions from "@mui/material/DialogActions";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import type { Theme } from "@mui/material/styles";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../types/hooks";
import Button from "./Button";
import StyledDataGrid, { DataGridToolbar } from "./StyledDataGrid";
import {
  useGetTagOptionsQuery,
  useCreateTagOptionMutation,
  useUpdateTagOptionMutation,
  useDeleteTagOptionMutation,
} from "../ducks/objectTags";
import { DEFAULT_TAG_COLOR, getContrastColor } from "./ObjectTags";
import softButtonsSx from "./softButtons";
import { useHasPermission } from "../ducks/profile";

const TAG_COLORS = [
  "#e57373",
  "#f06292",
  "#ba68c8",
  "#9575cd",
  "#7986cb",
  "#64b5f6",
  "#4dd0e1",
  "#4db6ac",
  "#81c784",
  "#aed581",
  "#ffd54f",
  "#ffb74d",
  "#a1887f",
  "#90a4ae",
  DEFAULT_TAG_COLOR,
];

const dialogPaperProps = {
  paper: {
    sx: (theme: Theme) => ({ borderRadius: "12px", ...softButtonsSx(theme) }),
  },
};

interface TagFormProps {
  form: { name: string; color: string };
  setForm: (form: { name: string; color: string }) => void;
  disabled: boolean;
  prefix: "create" | "edit";
}

const TagForm = ({ form, setForm, disabled, prefix }: TagFormProps) => (
  <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
    <TextField
      label="Name"
      value={form.name}
      onChange={(e) => setForm({ ...form, name: e.target.value })}
      fullWidth
      size="small"
      disabled={disabled}
      helperText="Letters and numbers only"
      slotProps={{
        htmlInput: { "data-testid": `${prefix}-tag-name-input` },
      }}
    />
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography variant="subtitle2">Color</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
        {TAG_COLORS.map((color) => {
          const selected = form.color.toLowerCase() === color;
          return (
            <Box
              key={color}
              component="button"
              type="button"
              aria-label={color}
              disabled={disabled}
              onClick={() => setForm({ ...form, color })}
              sx={{
                width: 28,
                height: 28,
                p: 0,
                borderRadius: "50%",
                bgcolor: color,
                border: 1,
                borderColor: "divider",
                cursor: "pointer",
                outline: selected ? "2px solid" : "none",
                outlineColor: "primary.main",
                outlineOffset: "2px",
                transition: "transform 0.1s",
                "&:hover": { transform: "scale(1.1)" },
              }}
            />
          );
        })}
        <Box
          sx={{
            width: 28,
            height: 28,
            p: "3px",
            borderRadius: "50%",
            background:
              "conic-gradient(#e57373, #ffd54f, #81c784, #4dd0e1, #7986cb, #ba68c8, #e57373)",
            outline: TAG_COLORS.includes(form.color.toLowerCase())
              ? "none"
              : "2px solid",
            outlineColor: "primary.main",
            outlineOffset: "2px",
          }}
        >
          <Box
            component="input"
            type="color"
            title="Custom color"
            value={form.color}
            onChange={(e: any) => setForm({ ...form, color: e.target.value })}
            disabled={disabled}
            data-testid={`${prefix}-tag-color-input`}
            sx={{
              display: "block",
              width: "100%",
              height: "100%",
              p: 0,
              border: 2,
              borderColor: "background.paper",
              borderRadius: "50%",
              bgcolor: "transparent",
              cursor: "pointer",
              overflow: "hidden",
              "&::-webkit-color-swatch-wrapper": { p: 0 },
              "&::-webkit-color-swatch": { border: "none" },
              "&::-moz-color-swatch": { border: "none" },
            }}
          />
        </Box>
      </Box>
    </Box>
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        py: 2,
        borderRadius: "8px",
        bgcolor: "action.hover",
      }}
    >
      <Chip
        label={form.name || "Preview"}
        sx={{
          bgcolor: form.color,
          color: getContrastColor(form.color),
          fontWeight: 500,
        }}
        data-testid={`${prefix}-tag-preview-chip`}
      />
    </Box>
  </Box>
);

const TagManagement = () => {
  const dispatch = useAppDispatch();
  const canManageSources = useHasPermission("Manage sources");

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingTag, setEditingTag] = useState<any>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    color: DEFAULT_TAG_COLOR,
  });
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    color: DEFAULT_TAG_COLOR,
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [tagToDelete, setTagToDelete] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const { data: tagOptions = [] } = useGetTagOptionsQuery();
  const [createTagOption] = useCreateTagOptionMutation();
  const [updateTagOption] = useUpdateTagOptionMutation();
  const [deleteTagOption] = useDeleteTagOptionMutation();

  const handleEditClick = (tag: any) => {
    setEditingTag(tag);
    setEditForm({
      name: tag.name,
      color: tag.color || DEFAULT_TAG_COLOR,
    });
    setEditDialogOpen(true);
  };

  const handleCreateClick = () => {
    setCreateForm({ name: "", color: DEFAULT_TAG_COLOR });
    setCreateDialogOpen(true);
  };

  const handleCreateSave = async () => {
    if (!createForm.name.trim()) {
      dispatch(showNotification("Tag name cannot be empty", "error"));
      return;
    }

    setLoading(true);
    try {
      await createTagOption({
        name: createForm.name,
        color: createForm.color,
      }).unwrap();
      dispatch(showNotification("Tag created successfully"));
      setCreateDialogOpen(false);
      setCreateForm({ name: "", color: DEFAULT_TAG_COLOR });
    } catch (error) {
      dispatch(showNotification("Failed to create tag", "error"));
    } finally {
      setLoading(false);
    }
  };

  const handleEditSave = async () => {
    if (!editForm.name.trim()) {
      dispatch(showNotification("Tag name cannot be empty", "error"));
      return;
    }

    setLoading(true);
    try {
      await updateTagOption({
        id: editingTag.id,
        name: editForm.name,
        color: editForm.color,
      }).unwrap();
      dispatch(showNotification("Tag updated successfully"));
      setEditDialogOpen(false);
      setEditingTag(null);
    } catch (error) {
      dispatch(showNotification("Failed to update tag", "error"));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (tag: any) => {
    setTagToDelete(tag);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setLoading(true);
    try {
      await deleteTagOption({ id: tagToDelete.id }).unwrap();
      dispatch(showNotification("Tag deleted successfully"));
      closeDeleteDialog();
    } catch (error) {
      dispatch(showNotification("Failed to delete tag", "error"));
    } finally {
      setLoading(false);
    }
  };

  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setTagToDelete(null);
  };

  const columns: any[] = [
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
    },
    {
      field: "name",
      headerName: "Tag Name",
      flex: 1,
      minWidth: 150,
      renderCell: (params: any) => {
        const tag = params.row;
        return (
          <Chip
            label={tag.name}
            size="small"
            sx={{
              minWidth: 60,
              bgcolor: tag.color || DEFAULT_TAG_COLOR,
              color: getContrastColor(tag.color || DEFAULT_TAG_COLOR),
            }}
          />
        );
      },
    },
    {
      field: "color",
      headerName: "Color",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => (
        <Box
          sx={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            border: 1,
            borderColor: "divider",
            bgcolor: params.row.color || DEFAULT_TAG_COLOR,
          }}
        />
      ),
    },
    {
      field: "created_at",
      headerName: "Created",
      flex: 1,
      minWidth: 120,
      valueGetter: (_value: any, row: any) =>
        row.created_at ? new Date(row.created_at).toLocaleDateString() : "N/A",
    },
    {
      field: "manage",
      headerName: "Manage",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => {
        const tag = params.row;
        if (!canManageSources) return null;
        return (
          <Box sx={{ display: "flex", gap: 0.25 }}>
            <Tooltip title="Edit tag">
              <IconButton
                size="small"
                onClick={() => handleEditClick(tag)}
                disabled={loading}
                data-testid={`edit-tag-button-${tag.id}`}
              >
                <EditIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete tag">
              <IconButton
                size="small"
                onClick={() => handleDeleteClick(tag)}
                disabled={loading}
                color="error"
                data-testid={`delete-tag-button-${tag.id}`}
              >
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </Box>
        );
      },
    },
  ];

  function CustomToolbar() {
    return (
      <DataGridToolbar showFilter showQuickFilter={false}>
        {canManageSources && (
          <Tooltip title="Create new tag">
            <IconButton
              onClick={handleCreateClick}
              disabled={loading}
              data-testid="create-tag-button"
            >
              <AddIcon />
            </IconButton>
          </Tooltip>
        )}
      </DataGridToolbar>
    );
  }

  return (
    <Box sx={{ p: 2 }} data-testid="tag-management-page">
      <Typography variant="h6" sx={{ mb: 1 }}>
        Source Tags Management
      </Typography>
      <StyledDataGrid
        autoHeight
        rows={tagOptions}
        columns={columns}
        getRowId={(row: any) => row.id}
        loading={loading}
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="xs"
        fullWidth
        slotProps={dialogPaperProps}
        data-testid="edit-tag-dialog"
      >
        <DialogTitle>Edit tag</DialogTitle>
        <DialogContent sx={{ pt: "0.5rem !important" }}>
          <TagForm
            form={editForm}
            setForm={setEditForm}
            disabled={loading}
            prefix="edit"
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            secondary
            onClick={() => setEditDialogOpen(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            primary
            onClick={handleEditSave}
            disabled={loading}
            data-testid="edit-tag-save-button"
          >
            {loading ? "Saving..." : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="xs"
        fullWidth
        slotProps={dialogPaperProps}
        data-testid="create-tag-dialog"
      >
        <DialogTitle>New tag</DialogTitle>
        <DialogContent sx={{ pt: "0.5rem !important" }}>
          <TagForm
            form={createForm}
            setForm={setCreateForm}
            disabled={loading}
            prefix="create"
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            secondary
            onClick={() => setCreateDialogOpen(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            primary
            onClick={handleCreateSave}
            disabled={loading}
            data-testid="create-tag-save-button"
          >
            {loading ? "Creating..." : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteDialogOpen}
        onClose={closeDeleteDialog}
        maxWidth="xs"
        fullWidth
        slotProps={dialogPaperProps}
        data-testid="delete-tag-dialog"
      >
        <DialogTitle data-testid="delete-tag-title">
          Delete tag: {tagToDelete?.name}
        </DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}
        >
          <Typography
            variant="body1"
            data-testid="delete-tag-confirmation-text"
          >
            Are you sure you want to delete the tag{" "}
            <strong>&quot;{tagToDelete?.name}&quot;</strong>?
          </Typography>
          <Typography
            variant="body2"
            color="error"
            data-testid="delete-tag-warning-text"
          >
            <strong>Warning:</strong> Deleting this tag will also remove all tag
            associations with sources.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            secondary
            onClick={closeDeleteDialog}
            disabled={loading}
            data-testid="delete-tag-cancel-button"
          >
            Cancel
          </Button>
          <Button
            primary
            color="error"
            onClick={handleDeleteConfirm}
            disabled={loading}
            data-testid="delete-tag-confirm-button"
          >
            {loading ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TagManagement;

import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
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
import DownloadIcon from "@mui/icons-material/Download";
import Box from "@mui/material/Box";
import { makeStyles } from "tss-react/mui";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
} from "@mui/x-data-grid";

import Button from "./Button";
import StyledDataGrid from "./StyledDataGrid";
import { showNotification } from "baselayer/components/Notifications";
import * as objectTagsActions from "../ducks/objectTags";
import { getContrastColor } from "./ObjectTags";

const useStyles = makeStyles()((theme) => ({
  root: {
    padding: theme.spacing(2),
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  manage: {
    display: "flex",
    flexDirection: "row",
    gap: "0.2rem",
  },
  colorChip: {
    minWidth: 60,
    height: 24,
  },
  editDialog: {
    minWidth: 400,
  },
  formControl: {
    minWidth: 200,
    marginTop: theme.spacing(1),
    marginBottom: theme.spacing(1),
  },
  colorPreview: {
    width: 24,
    height: 24,
    borderRadius: 4,
    border: "1px solid #ccc",
    marginRight: theme.spacing(1),
  },
  colorPicker: {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
}));

const TagManagement = () => {
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingTag, setEditingTag] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", color: "#dddfe2" });
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", color: "#dddfe2" });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [tagToDelete, setTagToDelete] = useState(null);
  const [loading, setLoading] = useState(false);

  const tagOptions = useSelector((state) => state.objectTags || []);

  useEffect(() => {
    dispatch(objectTagsActions.fetchTagOptions());
  }, [dispatch]);

  const handleEditClick = (tag) => {
    setEditingTag(tag);
    setEditForm({
      name: tag.name,
      color: tag.color || "#dddfe2",
    });
    setEditDialogOpen(true);
  };

  const handleCreateClick = () => {
    setCreateForm({ name: "", color: "#dddfe2" });
    setCreateDialogOpen(true);
  };

  const handleCreateSave = async () => {
    if (!createForm.name.trim()) {
      dispatch(showNotification("Tag name cannot be empty", "error"));
      return;
    }

    setLoading(true);
    try {
      const result = await dispatch(
        objectTagsActions.createTagOption({
          name: createForm.name,
          color: createForm.color,
        }),
      );

      if (result.status === "success") {
        dispatch(showNotification("Tag created successfully"));
        setCreateDialogOpen(false);
        setCreateForm({ name: "", color: "#dddfe2" });
        dispatch(objectTagsActions.fetchTagOptions());
      } else {
        dispatch(showNotification("Failed to create tag", "error"));
      }
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
      const result = await dispatch(
        objectTagsActions.updateTagOption({
          id: editingTag.id,
          name: editForm.name,
          color: editForm.color,
        }),
      );

      if (result.status === "success") {
        dispatch(showNotification("Tag updated successfully"));
        setEditDialogOpen(false);
        setEditingTag(null);
        dispatch(objectTagsActions.fetchTagOptions());
      } else {
        dispatch(showNotification("Failed to update tag", "error"));
      }
    } catch (error) {
      dispatch(showNotification("Failed to update tag", "error"));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (tag) => {
    setTagToDelete(tag);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setLoading(true);
    try {
      const result = await dispatch(
        objectTagsActions.deleteTagOption({ id: tagToDelete.id }),
      );

      if (result.status === "success") {
        dispatch(showNotification("Tag deleted successfully"));
        closeDeleteDialog();
        dispatch(objectTagsActions.fetchTagOptions());
      } else {
        dispatch(showNotification("Failed to delete tag", "error"));
      }
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

  const columns = [
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
      renderCell: (params) => {
        const tag = params.row;
        return (
          <Chip
            label={tag.name}
            className={classes.colorChip}
            style={{
              backgroundColor: tag.color || "#dddfe2",
              color: getContrastColor(tag.color || "#dddfe2"),
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
      renderCell: (params) => (
        <div
          className={classes.colorPreview}
          style={{ backgroundColor: params.row.color || "#dddfe2" }}
        />
      ),
    },
    {
      field: "created_at",
      headerName: "Created",
      flex: 1,
      minWidth: 120,
      valueGetter: (value, row) =>
        row.created_at ? new Date(row.created_at).toLocaleDateString() : "N/A",
    },
    {
      field: "manage",
      headerName: "Manage",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const tag = params.row;
        return (
          <div className={classes.manage}>
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
          </div>
        );
      },
    },
  ];

  const handleDownload = () => {
    if (!tagOptions?.length) {
      return;
    }
    const head = ["id", "name", "color", "created_at"];
    const csvCell = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const rows = tagOptions.map((tag) =>
      [tag.id, tag.name, tag.color, tag.created_at].map(csvCell).join(","),
    );
    const result = `${head.map(csvCell).join(",")}\n${rows.join("\n")}`;
    const blob = new Blob([result], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "tags.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  function CustomToolbar() {
    return (
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <GridToolbarFilterButton />
        <Tooltip title="Create new tag">
          <IconButton
            onClick={handleCreateClick}
            disabled={loading}
            data-testid="create-tag-button"
          >
            <AddIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Download CSV">
          <IconButton
            size="small"
            aria-label="Download CSV"
            data-testid="download-tags-button"
            onClick={handleDownload}
          >
            <DownloadIcon />
          </IconButton>
        </Tooltip>
      </GridToolbarContainer>
    );
  }

  return (
    <div className={classes.root} data-testid="tag-management-page">
      <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
        Source Tags Management
      </Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={tagOptions}
          columns={columns}
          getRowId={(row) => row.id}
          loading={loading}
          pageSizeOptions={[10, 25, 50, 100]}
          initialState={{
            pagination: { paginationModel: { pageSize: 10, page: 0 } },
          }}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Box>
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        className={classes.editDialog}
        maxWidth="sm"
        fullWidth
        data-testid="edit-tag-dialog"
      >
        <DialogTitle>Edit tag</DialogTitle>
        <DialogContent>
          <TextField
            label="Tag Name"
            value={editForm.name}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
            fullWidth
            margin="normal"
            variant="outlined"
            disabled={loading}
            inputProps={{ "data-testid": "edit-tag-name-input" }}
          />

          <div className={classes.colorPicker}>
            <Typography variant="body2">Color:</Typography>
            <input
              type="color"
              value={editForm.color}
              onChange={(e) =>
                setEditForm({ ...editForm, color: e.target.value })
              }
              data-testid="edit-tag-color-input"
              disabled={loading}
              style={{
                width: 40,
                height: 40,
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            />
            <Typography variant="body2">{editForm.color}</Typography>
          </div>

          <div>
            <Typography variant="subtitle2">Preview:</Typography>
            <Chip
              label={editForm.name || "Tag Preview"}
              style={{
                backgroundColor: editForm.color,
                color: getContrastColor(editForm.color),
                marginTop: 8,
              }}
              data-testid="edit-tag-preview-chip"
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setEditDialogOpen(false)}
            color="secondary"
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleEditSave}
            color="primary"
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
        className={classes.editDialog}
        maxWidth="sm"
        fullWidth
        data-testid="create-tag-dialog"
      >
        <DialogTitle>Create new tag</DialogTitle>
        <DialogContent>
          <TextField
            label="Tag Name"
            value={createForm.name}
            onChange={(e) =>
              setCreateForm({ ...createForm, name: e.target.value })
            }
            fullWidth
            margin="normal"
            variant="outlined"
            disabled={loading}
            helperText="Only letters and numbers, no spaces or special characters"
            inputProps={{ "data-testid": "create-tag-name-input" }}
          />

          <div className={classes.colorPicker}>
            <Typography variant="body2">Color:</Typography>
            <input
              type="color"
              value={createForm.color}
              onChange={(e) =>
                setCreateForm({ ...createForm, color: e.target.value })
              }
              disabled={loading}
              data-testid="create-tag-color-input"
              style={{
                width: 40,
                height: 40,
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            />
            <Typography variant="body2">{createForm.color}</Typography>
          </div>

          <div style={{ marginTop: "16px" }}>
            <Typography variant="subtitle2">Preview:</Typography>
            <Chip
              label={createForm.name || "Tag Preview"}
              style={{
                backgroundColor: createForm.color,
                color: getContrastColor(createForm.color),
                marginTop: 8,
              }}
              data-testid="create-tag-preview-chip"
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setCreateDialogOpen(false)}
            color="secondary"
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateSave}
            color="primary"
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
        maxWidth="sm"
        data-testid="delete-tag-dialog"
        fullWidth
      >
        <DialogTitle data-testid="delete-tag-title">
          Delete tag: {tagToDelete?.name}
        </DialogTitle>
        <DialogContent>
          <Typography
            variant="body1"
            gutterBottom
            data-testid="delete-tag-confirmation-text"
          >
            Are you sure you want to delete the tag{" "}
            <strong>&quot;{tagToDelete?.name}&quot;</strong>?
          </Typography>
          <Typography
            variant="body2"
            color="error"
            style={{ marginTop: "12px" }}
            data-testid="delete-tag-warning-text"
          >
            <strong>Warning:</strong> Deleting this tag will also remove all tag
            associations with sources.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={closeDeleteDialog}
            color="secondary"
            disabled={loading}
            data-testid="delete-tag-cancel-button"
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="primary"
            disabled={loading}
            data-testid="delete-tag-confirm-button"
          >
            {loading ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default TagManagement;

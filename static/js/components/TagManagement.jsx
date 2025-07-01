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
import makeStyles from "@mui/styles/makeStyles";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import MUIDataTable from "mui-datatables";

import Button from "./Button";
import { showNotification } from "baselayer/components/Notifications";
import * as objectTagsActions from "../ducks/objectTags";
import { getContrastColor } from "./ObjectTags";

const useStyles = makeStyles((theme) => ({
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

const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUITableCell: {
        styleOverrides: {
          paddingCheckbox: {
            padding: 0,
            margin: 0,
          },
        },
      },
      MUIDataTableBodyCell: {
        styleOverrides: {
          root: {
            padding: "0.25rem",
            paddingRight: 0,
            margin: 0,
          },
        },
      },
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: "0.5rem",
            paddingRight: 0,
            margin: 0,
          },
          sortLabelRoot: {
            height: "1.4rem",
          },
        },
      },
    },
  });

const TagManagement = () => {
  const classes = useStyles();
  const theme = useTheme();
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

  const renderManage = (dataIndex) => {
    const tag = tagOptions[dataIndex];
    return (
      <div className={classes.manage}>
        <Tooltip title="Edit tag">
          <IconButton
            size="small"
            onClick={() => handleEditClick(tag)}
            disabled={loading}
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
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </div>
    );
  };

  const columns = [
    {
      name: "id",
      label: "ID",
      options: {
        filter: false,
        sort: true,
      },
    },
    {
      name: "name",
      label: "Tag Name",
      options: {
        filter: true,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const tag = tagOptions[dataIndex];
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
    },
    {
      name: "color",
      label: "Color",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: (dataIndex) => {
          const tag = tagOptions[dataIndex];
          return (
            <div
              className={classes.colorPreview}
              style={{ backgroundColor: tag.color || "#dddfe2" }}
            />
          );
        },
      },
    },
    {
      name: "created_at",
      label: "Created",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const tag = tagOptions[dataIndex];
          return tag.created_at
            ? new Date(tag.created_at).toLocaleDateString()
            : "N/A";
        },
      },
    },
    {
      name: "manage",
      label: "Manage",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: renderManage,
      },
    },
  ];

  const customToolbar = () => (
    <Tooltip title="Create new tag">
      <IconButton onClick={handleCreateClick} disabled={loading}>
        <AddIcon />
      </IconButton>
    </Tooltip>
  );

  const options = {
    draggableColumns: { enabled: false },
    expandableRows: false,
    selectableRows: "none",
    filter: true,
    download: true,
    responsive: "standard",
    rowsPerPageOptions: [10, 25, 50, 100],
    customToolbar,
    textLabels: {
      body: {
        noMatch: "No tags found",
        toolTip: "Sort",
      },
      pagination: {
        next: "Next Page",
        previous: "Previous Page",
        rowsPerPage: "Rows per page:",
        displayRows: "of",
      },
      toolbar: {
        search: "Search",
        downloadCsv: "Download CSV",
        print: "Print",
        viewColumns: "View Columns",
        filterTable: "Filter Table",
      },
    },
  };

  return (
    <div className={classes.root}>
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable
            title="Source Tags Management"
            data={tagOptions}
            columns={columns}
            options={options}
          />
        </ThemeProvider>
      </StyledEngineProvider>

      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        className={classes.editDialog}
        maxWidth="sm"
        fullWidth
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
          />

          <div className={classes.colorPicker}>
            <Typography variant="body2">Color:</Typography>
            <input
              type="color"
              value={editForm.color}
              onChange={(e) =>
                setEditForm({ ...editForm, color: e.target.value })
              }
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
          <Button onClick={handleEditSave} color="primary" disabled={loading}>
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
          <Button onClick={handleCreateSave} color="primary" disabled={loading}>
            {loading ? "Creating..." : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteDialogOpen}
        onClose={closeDeleteDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Delete tag: {tagToDelete?.name}</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Are you sure you want to delete the tag{" "}
            <strong>&quot;{tagToDelete?.name}&quot;</strong>?
          </Typography>
          <Typography
            variant="body2"
            color="error"
            style={{ marginTop: "12px" }}
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
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="primary"
            disabled={loading}
            style={{ backgroundColor: "#d32f2f", color: "white" }}
          >
            {loading ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default TagManagement;

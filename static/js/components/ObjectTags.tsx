import { useState, useEffect } from "react";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogActions from "@mui/material/DialogActions";
import Divider from "@mui/material/Divider";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import { Controller, useForm } from "react-hook-form";
import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import GroupShareSelect from "./group/GroupShareSelect";
import EditTagGroups from "./EditTagGroups";
import { useAppDispatch, useAppSelector } from "../types/hooks";
import * as objectTagsActions from "../ducks/objectTags";
import * as groupsActions from "../ducks/groups";

const useStyles = makeStyles()((theme) => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
  addButton: {
    height: "0.75rem",
    cursor: "pointer",
  },
  loadingIcon: {
    marginLeft: theme.spacing(1),
    fontSize: "0.875rem",
  },
  divider: {
    marginTop: theme.spacing(3),
    marginBottom: theme.spacing(2),
  },
  newTagField: {
    width: "100%",
  },
  colorPicker: {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
}));

export const getContrastColor = (hexColor: string) => {
  if (!hexColor || hexColor.length !== 7) return "#000000";

  const r = parseInt(hexColor.substr(1, 2), 16);
  const g = parseInt(hexColor.substr(3, 2), 16);
  const b = parseInt(hexColor.substr(5, 2), 16);

  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "#000000" : "#ffffff";
};

interface ObjectTagsProps {
  source: any;
}

const ObjectTags = ({ source }: ObjectTagsProps) => {
  const { classes: styles } = useStyles() as { classes: any };
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState<any>(null);
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("#dddfe2");
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  const [tagError, setTagError] = useState("");
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [editingTag, setEditingTag] = useState<any>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const tagOptions = useAppSelector((state) => state.objectTags || []);
  const currentUser = useAppSelector((state) => state.profile);
  const groups = useAppSelector((state) => state.groups.userAccessible);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage sources");

  const { control, setValue, getValues } = useForm();

  useEffect(() => {
    if (!tagOptions || tagOptions.length === 0) {
      dispatch(objectTagsActions.fetchTagOptions());
    }
    if (!groups || groups.length === 0) {
      dispatch(groupsActions.fetchGroups());
    }
  }, [dispatch]);

  const handleOpenDialog = () => {
    setOpen(true);
    setNewTagName("");
    setSelectedTag(null);
    setValue("tag", null);
    setNewTagColor("#dddfe2");
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setSelectedTag(null);
    setValue("tag", null);
    setNewTagName("");
    setNewTagColor("#dddfe2");
    setSelectedGroupIds([]);
  };

  const handleOpenEditDialog = (tag: any) => {
    setEditingTag(tag);
    setEditDialogOpen(true);
  };

  const handleCloseEditDialog = () => {
    setEditDialogOpen(false);
    setEditingTag(null);
  };

  const handleNewTagNameChange = (event: any) => {
    setNewTagName(event.target.value);
    setTagError("");
  };

  const handleCreateTag = () => {
    if (!newTagName.trim()) {
      setTagError("Tag name cannot be empty");
      return;
    }

    setIsCreatingTag(true);

    dispatch(
      objectTagsActions.createTagOption({
        name: newTagName,
        color: newTagColor,
      }),
    ).then((result: any) => {
      setIsCreatingTag(false);

      if (result.status === "success") {
        dispatch(showNotification("Tag created successfully"));
        dispatch(objectTagsActions.fetchTagOptions()).then(() => {
          if (result.data) {
            setSelectedTag(result.data);
            setValue("tag", result.data);
          }
        });
        setNewTagName("");
        setNewTagColor("#dddfe2");
      } else {
        const errorMsg = result.message || "Failed to create tag";
        setTagError(errorMsg);
        dispatch(showNotification(errorMsg, "error"));
      }
    });
  };

  const handleAddTag = () => {
    const formValues = getValues();
    const tagToAdd = formValues["tag"];

    setIsAddingTag(true);

    dispatch(
      objectTagsActions.addObjectTag({
        obj_id: source.id,
        objtagoption_id: tagToAdd.id,
        group_ids: selectedGroupIds,
      }),
    ).then((result: any) => {
      setIsAddingTag(false);
      if (result.status === "success") {
        dispatch(showNotification("Tag added successfully"));
        handleCloseDialog();
      } else {
        dispatch(showNotification("Failed to add tag", "error"));
      }
    });
  };

  const usedTagIds = (source.tags || []).map((tag: any) => tag.objtagoption_id);
  const availableTags = tagOptions.filter(
    (tag: any) => !usedTagIds.includes(tag.id),
  );

  const sourceGroupIds = source.groups?.map((g: any) => g.id) || [];
  const availableGroups = (groups || []).filter(
    (g: any) => sourceGroupIds.length === 0 || sourceGroupIds.includes(g.id),
  );

  const sourceTagsWithColors = (source.tags || []).map((tag: any) => {
    const tagOption: any = tagOptions.find(
      (option: any) => option.id === tag.objtagoption_id,
    );
    return {
      ...tag,
      color: tagOption?.color || "#dddfe2",
      groups: tag.groups || [],
    };
  });

  return (
    <div className={styles.root}>
      <div className={styles.chips}>
        {sourceTagsWithColors.map((tag: any) => {
          // Meta-object provenance: a tag aggregated from a linked source keeps
          // its own obj_id. Surface where it came from, and don't offer to edit
          // it from this page (writes stay per-source).
          const fromLinkedObj = tag.obj_id && tag.obj_id !== source.id;
          const chip = (
            <Chip
              key={tag.id}
              className={styles.chip}
              label={fromLinkedObj ? `${tag.name} (${tag.obj_id})` : tag.name}
              size="small"
              deleteIcon={fromLinkedObj ? undefined : <EditIcon />}
              onDelete={
                fromLinkedObj ? undefined : () => handleOpenEditDialog(tag)
              }
              data-testid={`tag-chip-${tag.id}`}
              style={{
                backgroundColor: tag.color,
                color: getContrastColor(tag.color),
              }}
            />
          );
          return fromLinkedObj ? (
            <Tooltip key={tag.id} title={`From linked source ${tag.obj_id}`}>
              {chip}
            </Tooltip>
          ) : (
            chip
          );
        })}
      </div>

      <Tooltip title="Add Tag">
        <IconButton
          size="small"
          className={styles.addButton}
          onClick={handleOpenDialog}
          data-testid="add-tag-button"
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      <Dialog
        open={open}
        onClose={handleCloseDialog}
        maxWidth="xs"
        fullWidth
        data-testid="add-tag-dialog"
      >
        <DialogTitle>Add Tag to {source.id}</DialogTitle>
        <DialogContent style={{ marginTop: "0.5rem", overflow: "visible" }}>
          {availableTags.length > 0 ? (
            <Controller
              name="tag"
              control={control}
              render={({ field: { onChange, value } }) => {
                return (
                  <Autocomplete
                    id="tagSelect"
                    options={availableTags}
                    getOptionLabel={(option: any) => option.name}
                    value={value}
                    onChange={(_, data) => {
                      onChange(data);
                      setSelectedTag(data);
                    }}
                    renderOption={(props, option: any) => (
                      <li {...props}>
                        <Chip
                          label={option.name}
                          size="small"
                          style={{
                            backgroundColor: option.color || "#dddfe2",
                            color: getContrastColor(option.color || "#dddfe2"),
                            marginRight: 8,
                          }}
                        />
                      </li>
                    )}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        variant="outlined"
                        label="Select Tag"
                        size="small"
                        className={styles.autocomplete}
                        data-testid="tag-autocomplete-input"
                      />
                    )}
                    filterSelectedOptions
                    data-testid="tag-select"
                  />
                );
              }}
            />
          ) : (
            <Typography variant="body2" color="textSecondary">
              No (more) available tags to add to this source.
            </Typography>
          )}

          {availableTags.length > 0 &&
            (availableGroups.length > 0 ? (
              <>
                <GroupShareSelect
                  groupList={availableGroups}
                  groupIDs={selectedGroupIds}
                  setGroupIDs={setSelectedGroupIds}
                />
                {selectedGroupIds.length === 0 && (
                  <Typography
                    variant="caption"
                    color="textSecondary"
                    style={{ marginTop: "0.25rem", display: "block" }}
                  >
                    No group selected — will default to the sitewide group.
                  </Typography>
                )}
              </>
            ) : (
              <Typography
                variant="body2"
                color="error"
                style={{ marginTop: "1rem" }}
              >
                No groups available. Please ensure you have access to at least
                one group.
              </Typography>
            ))}

          {permission && (
            <>
              <Divider className={styles.divider} />

              <div className={styles.createTagSection}>
                <Typography variant="subtitle1" gutterBottom>
                  Create New Tag
                </Typography>

                <TextField
                  label="New Tag Name"
                  value={newTagName}
                  onChange={handleNewTagNameChange}
                  variant="outlined"
                  size="small"
                  className={styles.newTagField}
                  error={!!tagError}
                  helperText={
                    tagError ||
                    "Only letters and numbers, no spaces or special characters"
                  }
                  disabled={isCreatingTag}
                  inputProps={{
                    "data-testid": "new-tag-input",
                  }}
                />
                <div className={styles.colorPicker}>
                  <Typography variant="body2">Color:</Typography>
                  <input
                    type="color"
                    value={newTagColor}
                    onChange={(e) => setNewTagColor(e.target.value)}
                    style={{
                      width: 40,
                      height: 40,
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  />
                  <Typography variant="body2">{newTagColor}</Typography>
                </div>
                <Button
                  color="primary"
                  onClick={handleCreateTag}
                  disabled={!newTagName || isCreatingTag}
                  data-testid="create-tag-button"
                >
                  {isCreatingTag ? "Creating..." : "Create Tag"}
                  {isCreatingTag && (
                    <CircularProgress
                      size={16}
                      className={styles.loadingIcon}
                    />
                  )}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} color="secondary">
            Cancel
          </Button>
          <Button
            onClick={handleAddTag}
            color="primary"
            disabled={!selectedTag || isAddingTag}
            data-testid="save-tag-button"
          >
            {isAddingTag ? "Saving..." : "Save"}
            {isAddingTag && (
              <CircularProgress size={16} className={styles.loadingIcon} />
            )}
          </Button>
        </DialogActions>
      </Dialog>

      <EditTagGroups
        tag={editingTag}
        source={source}
        groups={availableGroups}
        open={editDialogOpen}
        onClose={handleCloseEditDialog}
      />
    </div>
  );
};

export default ObjectTags;

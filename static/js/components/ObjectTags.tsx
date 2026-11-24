import { useGetProfileQuery } from "../ducks/profile";
import { useState } from "react";
import EditIcon from "@mui/icons-material/Edit";
import CancelIcon from "@mui/icons-material/Cancel";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import DialogActions from "@mui/material/DialogActions";
import CircularProgress from "@mui/material/CircularProgress";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import softButtonsSx from "./softButtons";
import GroupShareSelect from "./group/GroupShareSelect";
import EditTagGroups from "./EditTagGroups";
import { useAppDispatch } from "../types/hooks";
import {
  useGetTagOptionsQuery,
  useCreateTagOptionMutation,
  useAddObjectTagMutation,
  useDeleteObjectTagMutation,
} from "../ducks/objectTags";
import { useGetGroupsQuery } from "../ducks/groups";

const DEFAULT_TAG_COLOR = "#dddfe2";

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
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [selectedTag, setSelectedTag] = useState<any>(null);
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState(DEFAULT_TAG_COLOR);
  const [tagFilter, setTagFilter] = useState("");
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  const [tagError, setTagError] = useState("");
  const [selectedGroupIds, setSelectedGroupIds] = useState<any[]>([]);
  const [editingTag, setEditingTag] = useState<any>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const { data: tagOptions = [] } = useGetTagOptionsQuery();
  const [createTagOption] = useCreateTagOptionMutation();
  const [addObjectTag] = useAddObjectTagMutation();
  const [deleteObjectTag] = useDeleteObjectTagMutation();
  const { data: currentUser } = useGetProfileQuery();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage sources");

  const handleOpenDialog = () => {
    setOpen(true);
    setNewTagName("");
    setSelectedTag(null);
    setTagFilter("");
    setNewTagColor(DEFAULT_TAG_COLOR);
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setSelectedTag(null);
    setNewTagName("");
    setNewTagColor(DEFAULT_TAG_COLOR);
    setSelectedGroupIds([]);
  };

  const handleOpenEditDialog = (tag: any) => {
    setEditingTag(tag);
    setEditDialogOpen(true);
  };

  const removeTag = async (tag: any) => {
    const { error } = await deleteObjectTag({ id: tag.id });
    if (!error) dispatch(showNotification("Tag removed from source"));
  };

  const handleCloseEditDialog = () => {
    setEditDialogOpen(false);
    setEditingTag(null);
  };

  const handleNewTagNameChange = (event: any) => {
    setNewTagName(event.target.value);
    setTagError("");
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim()) {
      setTagError("Tag name cannot be empty");
      return;
    }

    setIsCreatingTag(true);

    try {
      const created: any = await createTagOption({
        name: newTagName,
        color: newTagColor,
      }).unwrap();
      dispatch(showNotification("Tag created successfully"));
      if (created) setSelectedTag(created);
      setNewTagName("");
      setNewTagColor(DEFAULT_TAG_COLOR);
    } catch (error: any) {
      const errorMsg = error?.message || "Failed to create tag";
      setTagError(errorMsg);
      dispatch(showNotification(errorMsg, "error"));
    } finally {
      setIsCreatingTag(false);
    }
  };

  const handleAddTag = async () => {
    setIsAddingTag(true);

    try {
      await addObjectTag({
        obj_id: source.id,
        objtagoption_id: selectedTag.id,
        group_ids: selectedGroupIds,
      }).unwrap();
      dispatch(showNotification("Tag added successfully"));
      handleCloseDialog();
    } catch (error) {
      dispatch(showNotification("Failed to add tag", "error"));
    } finally {
      setIsAddingTag(false);
    }
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
      color: tagOption?.color || DEFAULT_TAG_COLOR,
      groups: tag.groups || [],
    };
  });

  const query = tagFilter.trim().toLowerCase();
  const shownTags = query
    ? availableTags.filter((tag: any) => tag.name.toLowerCase().includes(query))
    : availableTags;

  return (
    <Box
      sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}
    >
      {sourceTagsWithColors.map((tag: any) => {
        // Meta-object provenance: a tag aggregated from a linked source keeps
        // its own obj_id. Surface where it came from, and don't offer to edit
        // it from this page (writes stay per-source).
        const fromLinkedObj = tag.obj_id && tag.obj_id !== source.id;
        const editable = availableGroups.length > 0;
        const chip = (
          <Chip
            key={tag.id}
            label={fromLinkedObj ? `${tag.name} (${tag.obj_id})` : tag.name}
            size="small"
            deleteIcon={
              fromLinkedObj ? undefined : editable ? (
                <Tooltip title="Edit tag">
                  <EditIcon />
                </Tooltip>
              ) : (
                <Tooltip title="Remove tag">
                  <CancelIcon />
                </Tooltip>
              )
            }
            onDelete={
              fromLinkedObj
                ? undefined
                : editable
                  ? () => handleOpenEditDialog(tag)
                  : () => removeTag(tag)
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

      <Chip
        size="small"
        variant="outlined"
        component="button"
        label="Add tag"
        onClick={handleOpenDialog}
        data-testid="add-tag-button"
        sx={{
          borderStyle: "dashed",
          color: "text.secondary",
          "&:hover": { borderColor: "primary.main", color: "primary.main" },
        }}
      />

      <Dialog
        open={open}
        onClose={handleCloseDialog}
        maxWidth="xs"
        fullWidth
        data-testid="add-tag-dialog"
        slotProps={{
          paper: {
            sx: (theme) => ({ borderRadius: "12px", ...softButtonsSx(theme) }),
          },
        }}
      >
        <DialogTitle sx={{ pb: 0 }}>
          Add a tag
          <Typography variant="body2" color="text.secondary">
            {source.id}
          </Typography>
        </DialogTitle>
        <DialogContent
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            pt: "1rem !important",
          }}
        >
          {availableTags.length > 0 ? (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <TextField
                size="small"
                fullWidth
                placeholder="Search tags"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                slotProps={{
                  htmlInput: { "data-testid": "tag-search-input" },
                }}
              />
              <Box
                data-testid="tag-select"
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 0.75,
                  maxHeight: 180,
                  overflowY: "auto",
                  p: 0.5,
                }}
              >
                {shownTags.map((tag: any) => {
                  const color = tag.color || DEFAULT_TAG_COLOR;
                  return (
                    <Chip
                      key={tag.id}
                      size="small"
                      label={tag.name}
                      onClick={() => setSelectedTag(tag)}
                      data-testid={`tag-option-${tag.name}`}
                      sx={{
                        bgcolor: color,
                        color: getContrastColor(color),
                        outline:
                          selectedTag?.id === tag.id ? "2px solid" : "none",
                        outlineColor: "primary.main",
                        outlineOffset: "2px",
                        "&:hover, &:focus-visible": {
                          bgcolor: color,
                          filter: "brightness(0.92)",
                        },
                      }}
                    />
                  );
                })}
                {shownTags.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No matching tag
                  </Typography>
                )}
              </Box>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No more tags to add to this source.
            </Typography>
          )}

          {availableTags.length > 0 &&
            (availableGroups.length > 0 ? (
              <Box>
                <GroupShareSelect
                  groupList={availableGroups}
                  groupIDs={selectedGroupIds}
                  setGroupIDs={setSelectedGroupIds}
                />
                {selectedGroupIds.length === 0 && (
                  <Typography variant="caption" color="text.secondary">
                    Defaults to the sitewide group
                  </Typography>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="error">
                You have no group to share this tag with.
              </Typography>
            ))}

          {permission && (
            <Box
              data-testid="create-tag-section"
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 1,
                pt: 2,
                borderTop: 1,
                borderColor: "divider",
              }}
            >
              <Typography variant="subtitle2">New tag</Typography>
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
                <Tooltip title="Color">
                  <Box
                    component="input"
                    type="color"
                    value={newTagColor}
                    onChange={(e: any) => setNewTagColor(e.target.value)}
                    sx={{
                      width: 40,
                      height: 40,
                      flexShrink: 0,
                      p: 0.5,
                      border: 1,
                      borderColor: "divider",
                      borderRadius: "8px",
                      bgcolor: "transparent",
                      cursor: "pointer",
                    }}
                  />
                </Tooltip>
                <TextField
                  size="small"
                  fullWidth
                  placeholder="Name"
                  value={newTagName}
                  onChange={handleNewTagNameChange}
                  error={!!tagError}
                  helperText={tagError || "Letters and numbers only"}
                  disabled={isCreatingTag}
                  slotProps={{
                    htmlInput: {
                      "data-testid": "new-tag-input",
                    },
                  }}
                />
                <Button
                  secondary
                  onClick={handleCreateTag}
                  disabled={!newTagName || isCreatingTag}
                  data-testid="create-tag-button"
                  sx={{ height: 40, flexShrink: 0 }}
                >
                  {isCreatingTag ? <CircularProgress size={16} /> : "Create"}
                </Button>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            primary
            onClick={handleAddTag}
            disabled={!selectedTag || isAddingTag}
            data-testid="save-tag-button"
          >
            {isAddingTag ? "Adding..." : "Add tag"}
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
    </Box>
  );
};

export default ObjectTags;

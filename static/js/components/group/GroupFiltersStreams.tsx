import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import MuiButton from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemSecondaryAction from "@mui/material/ListItemSecondaryAction";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";

import Button from "../Button";
import ConfirmFilterDeletionDialog from "../filter/ConfirmFilterDeletionDialog";
import NewFilterDialog from "../filter/NewFilterDialog";

import { useAppDispatch } from "../../types/hooks";
import {
  useDeleteGroupFilterMutation,
  useUpdateFilterNameMutation,
} from "../../ducks/filter";
import { groupApi } from "../../ducks/group";
import {
  useGetStreamsQuery,
  useAddGroupStreamMutation,
} from "../../ducks/streams";

interface GroupFiltersStreamsProps {
  group: any;
  currentUser: any;
  isAdmin: (...args: any[]) => any;
}

const GroupFiltersStreams = ({
  group,
  currentUser,
  isAdmin,
}: GroupFiltersStreamsProps) => {
  const [filterStreamId, setFilterStreamId] = useState<number | null>(null);
  const [addStreamOpen, setAddStreamOpen] = useState(false);
  const [newStreamId, setNewStreamId] = useState<number | "">("");
  const [editingFilterId, setEditingFilterId] = useState<number | null>(null);
  const [editNameInput, setEditNameInput] = useState("");
  const [filterToDelete, setFilterToDelete] = useState<any>(null);
  const dispatch = useAppDispatch();
  const { data: streams } = useGetStreamsQuery();
  const [deleteGroupFilter] = useDeleteGroupFilterMutation();
  const [addGroupStream] = useAddGroupStreamMutation();
  const [updateFilterName] = useUpdateFilterNameMutation();

  const canEdit = isAdmin(currentUser);
  const groupStreamIds = group.streams?.map((stream: any) => stream.id) ?? [];
  const refreshGroup = () =>
    dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));

  const onAddStream = async () => {
    try {
      await addGroupStream({
        group_id: group.id,
        stream_id: newStreamId,
      }).unwrap();
      dispatch(showNotification("Added stream to group"));
      refreshGroup();
      setAddStreamOpen(false);
    } catch {
      // error notification handled by the base query
    }
  };

  const handleDeleteFilter = async () => {
    try {
      await deleteGroupFilter({ filter_id: filterToDelete.id }).unwrap();
      dispatch(showNotification("Deleted filter from group"));
    } catch {
      // error notification handled by the base query
    }
    setFilterToDelete(null);
    refreshGroup();
  };

  const handleSaveRename = async () => {
    const trimmed = editNameInput.trim();
    if (!trimmed) {
      dispatch(showNotification("Filter name cannot be empty.", "error"));
      return;
    }
    try {
      await updateFilterName({
        filter_id: editingFilterId!,
        name: trimmed,
      }).unwrap();
      dispatch(showNotification("Filter name updated."));
      refreshGroup();
    } catch {
      // error notification handled by the base query
    }
    setEditingFilterId(null);
  };

  if (!streams?.length) return null;

  return (
    <Box sx={{ p: 1.5 }}>
      <Typography variant="h6">Streams and filters</Typography>
      <Paper sx={{ mb: 1 }}>
        <List component="nav">
          {group.streams?.length ? (
            group.streams.map((stream: any) => (
              <Fragment key={stream.id}>
                <ListItem
                  secondaryAction={
                    canEdit && (
                      <Tooltip
                        title={`Add filter to stream "${stream.name}"`}
                        placement="left"
                      >
                        <IconButton
                          edge="end"
                          aria-label="add filter"
                          onClick={() => setFilterStreamId(stream.id)}
                        >
                          <AddIcon />
                        </IconButton>
                      </Tooltip>
                    )
                  }
                >
                  <ListItemText primary={stream.name} />
                </ListItem>
                <List disablePadding>
                  {(group.filters ?? [])
                    .filter((filter: any) => filter.stream_id === stream.id)
                    .map((filter: any) =>
                      editingFilterId === filter.id ? (
                        <ListItem key={filter.id} sx={{ pl: 2 }}>
                          <TextField
                            value={editNameInput}
                            onChange={(e) => setEditNameInput(e.target.value)}
                            size="small"
                            slotProps={{
                              htmlInput: { "data-testid": "filter-name-input" },
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveRename();
                              if (e.key === "Escape") setEditingFilterId(null);
                            }}
                            autoFocus
                          />
                          <ListItemSecondaryAction>
                            <IconButton
                              size="small"
                              onClick={handleSaveRename}
                              aria-label="save filter name"
                              data-testid="save-filter-name-button"
                            >
                              <CheckIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              onClick={() => setEditingFilterId(null)}
                              aria-label="cancel filter rename"
                            >
                              <CloseIcon fontSize="small" />
                            </IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ) : (
                        <ListItemButton
                          key={filter.id}
                          component={Link}
                          to={`/filter/${filter.id}`}
                        >
                          <ListItemText sx={{ pl: 2 }} primary={filter.name} />
                          {canEdit && (
                            <ListItemSecondaryAction>
                              <Tooltip
                                title={`Rename filter "${filter.name}"`}
                                placement="left"
                              >
                                <IconButton
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    setEditingFilterId(filter.id);
                                    setEditNameInput(filter.name);
                                  }}
                                  aria-label="rename filter"
                                  data-testid={`rename-filter-${filter.id}`}
                                >
                                  <EditIcon />
                                </IconButton>
                              </Tooltip>
                              <Tooltip
                                title={`Delete filter "${filter.name}"`}
                                placement="left"
                              >
                                <IconButton
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    setFilterToDelete(filter);
                                  }}
                                  color="error"
                                  aria-label="delete filter"
                                >
                                  <DeleteIcon />
                                </IconButton>
                              </Tooltip>
                            </ListItemSecondaryAction>
                          )}
                        </ListItemButton>
                      ),
                    )}
                </List>
              </Fragment>
            ))
          ) : (
            <ListItem>
              <ListItemText secondary="No streams available for this group." />
            </ListItem>
          )}
        </List>
      </Paper>
      {currentUser.permissions.includes("System admin") && (
        <Button
          primary
          onClick={() => {
            setNewStreamId("");
            setAddStreamOpen(true);
          }}
          disabled={groupStreamIds.length >= streams.length}
        >
          Add stream
        </Button>
      )}
      <Dialog
        open={addStreamOpen}
        onClose={() => setAddStreamOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add stream to group</DialogTitle>
        <DialogContent dividers>
          <FormControl size="small" fullWidth>
            <InputLabel id="alert-stream-select-required-label">
              Alert stream
            </InputLabel>
            <Select
              label="Alert stream"
              labelId="alert-stream-select-required-label"
              value={newStreamId}
              onChange={(e) => setNewStreamId(e.target.value as number)}
            >
              {streams
                .filter((stream: any) => !groupStreamIds.includes(stream.id))
                .map((stream: any) => (
                  <MenuItem value={stream.id} key={stream.id}>
                    {stream.name}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <MuiButton onClick={() => setAddStreamOpen(false)}>Cancel</MuiButton>
          <MuiButton
            variant="contained"
            disabled={newStreamId === ""}
            onClick={onAddStream}
            data-testid="add-stream-dialog-submit"
          >
            Add
          </MuiButton>
        </DialogActions>
      </Dialog>
      {filterStreamId !== null && (
        <NewFilterDialog
          open
          onClose={() => setFilterStreamId(null)}
          groupId={group.id}
          streamId={filterStreamId}
        />
      )}
      <ConfirmFilterDeletionDialog
        filter={filterToDelete}
        closeDialog={() => setFilterToDelete(null)}
        deleteFunction={handleDeleteFilter}
      />
    </Box>
  );
};

export default GroupFiltersStreams;

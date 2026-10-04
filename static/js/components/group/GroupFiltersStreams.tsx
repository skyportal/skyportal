import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
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
  useUpdateFilterMutation,
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
  const [updateFilter] = useUpdateFilterMutation();

  const canEdit = isAdmin(currentUser);
  const groupStreamIds = group.streams?.map((stream: any) => stream.id) ?? [];
  const refreshGroup = () =>
    dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));

  const onAddStream = async () => {
    const { error } = await addGroupStream({
      group_id: group.id,
      stream_id: newStreamId,
    });
    if (error) return;
    dispatch(showNotification("Added stream to group"));
    refreshGroup();
    setAddStreamOpen(false);
  };

  const handleDeleteFilter = async () => {
    const { error } = await deleteGroupFilter({ filter_id: filterToDelete.id });
    if (!error) dispatch(showNotification("Deleted filter from group"));
    setFilterToDelete(null);
    refreshGroup();
  };

  const handleSaveRename = async () => {
    const name = editNameInput.trim();
    if (!name) {
      dispatch(showNotification("Filter name cannot be empty.", "error"));
      return;
    }
    const { error } = await updateFilter({ filter_id: editingFilterId!, name });
    if (!error) {
      dispatch(showNotification("Filter name updated."));
      refreshGroup();
    }
    setEditingFilterId(null);
  };

  if (!streams?.length) return null;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, p: 1.5 }}>
      <Typography variant="h6">Streams and filters</Typography>
      <Paper>
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
                        <ListItem key={filter.id}>
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
                          <IconButton
                            size="small"
                            color="success"
                            onClick={handleSaveRename}
                            aria-label="save filter name"
                            data-testid="save-filter-name-button"
                          >
                            <CheckIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => setEditingFilterId(null)}
                            aria-label="cancel filter rename"
                          >
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        </ListItem>
                      ) : (
                        <ListItem key={filter.id} disablePadding>
                          <ListItemButton
                            component={Link}
                            to={`/filter/${filter.id}`}
                            sx={{ flexGrow: 0, pr: 1 }}
                          >
                            <ListItemText
                              sx={{ pl: 2 }}
                              primary={filter.name}
                            />
                          </ListItemButton>
                          {canEdit && (
                            <>
                              <Tooltip title={`Rename filter "${filter.name}"`}>
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    setEditingFilterId(filter.id);
                                    setEditNameInput(filter.name);
                                  }}
                                  aria-label="rename filter"
                                  data-testid={`rename-filter-${filter.id}`}
                                >
                                  <EditIcon sx={{ fontSize: 16 }} />
                                </IconButton>
                              </Tooltip>
                              <Tooltip
                                title={`Delete filter "${filter.name}"`}
                                placement="left"
                              >
                                <IconButton
                                  onClick={() => setFilterToDelete(filter)}
                                  color="error"
                                  aria-label="delete filter"
                                  sx={{ ml: "auto", mr: 2 }}
                                >
                                  <DeleteIcon />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                        </ListItem>
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
          sx={{ alignSelf: "flex-start" }}
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
          <TextField
            select
            fullWidth
            size="small"
            id="alert-stream-select-required"
            label="Alert stream"
            value={newStreamId}
            onChange={(e) => setNewStreamId(Number(e.target.value))}
          >
            {streams
              .filter((stream: any) => !groupStreamIds.includes(stream.id))
              .map((stream: any) => (
                <MenuItem value={stream.id} key={stream.id}>
                  {stream.name}
                </MenuItem>
              ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddStreamOpen(false)}>Cancel</Button>
          <Button
            primary
            disabled={newStreamId === ""}
            onClick={onAddStream}
            data-testid="add-stream-dialog-submit"
          >
            Add
          </Button>
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

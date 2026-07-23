import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { Controller, useForm } from "react-hook-form";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import Tooltip from "@mui/material/Tooltip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemSecondaryAction from "@mui/material/ListItemSecondaryAction";
import ListItemText from "@mui/material/ListItemText";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

import { Box } from "@mui/material";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormHelperText from "@mui/material/FormHelperText";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import Paper from "@mui/material/Paper";
import ListItemButton from "@mui/material/ListItemButton";
import { showNotification } from "baselayer/components/Notifications";

import Button from "../Button";

import { useAppDispatch } from "../../types/hooks";
import {
  useAddGroupFilterMutation,
  useDeleteGroupFilterMutation,
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
  theme: any;
}

const GroupFiltersStreams = ({
  group,
  currentUser,
  isAdmin,
  theme,
}: GroupFiltersStreamsProps) => {
  const [filterStream, setFilterStream] = useState<any>(null);
  const [addStreamOpen, setAddStreamOpen] = useState(false);
  const dispatch = useAppDispatch();
  const { data: streams } = useGetStreamsQuery();
  const [addGroupFilter] = useAddGroupFilterMutation();
  const [deleteGroupFilter] = useDeleteGroupFilterMutation();
  const [addGroupStream] = useAddGroupStreamMutation();

  const { register, handleSubmit, control, reset } = useForm();

  const { handleSubmit: handleSubmit2, control: control2 } = useForm();

  const fullScreen = !useMediaQuery(theme.breakpoints.up("md"));

  const handleAddFilterDialogClose = () => {
    setFilterStream(null);
  };

  const handleAddFilterDialogOpen = (stream: any) => {
    reset({ filter_name: "" });
    setFilterStream(stream);
  };

  const handleAddStreamClose = () => {
    setAddStreamOpen(false);
  };
  const onSubmitAddFilter = async (data: any) => {
    try {
      await addGroupFilter({
        name: data.filter_name,
        group_id: group.id,
        stream_id: filterStream.id,
      }).unwrap();
      dispatch(showNotification("Added filter to group"));
      dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));
      handleAddFilterDialogClose();
    } catch {
      // error notification handled by the base query
    }
  };

  const onSubmitAddStream = async (data: any) => {
    try {
      await addGroupStream({
        group_id: group.id,
        stream_id: data.stream_id,
      }).unwrap();
      dispatch(showNotification("Added stream to group"));
      dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));
      setAddStreamOpen(false);
    } catch {
      // error notification handled by the base query
    }
  };

  const groupStreamIds = group?.streams?.map((stream: any) => stream.id);

  const isStreamIdInStreams = (sid: any) =>
    streams?.map((stream: any) => stream.id).includes(sid);

  const filtersByStreamId = (group.filters ?? []).reduce(
    (acc: any, filter: any) => {
      (acc[filter.stream_id] ??= []).push(filter);
      return acc;
    },
    {},
  );

  const handleDeleteFilter = async (filterId: any) => {
    try {
      await deleteGroupFilter({ filter_id: filterId }).unwrap();
      dispatch(showNotification("Deleted filter from group"));
    } catch {
      // error notification handled by the base query
    }
    dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));
  };

  if (!streams?.length) return null;

  return (
    <Box sx={{ p: 1.5 }}>
      <Typography variant="h6">Streams and filters</Typography>
      <Paper sx={{ mb: 1 }}>
        <List component="nav">
          {group.streams?.map((stream: any) => (
            <Fragment key={stream.id}>
              <ListItem
                secondaryAction={
                  isAdmin(currentUser) && (
                    <Tooltip
                      title={`Add filter to stream "${stream.name}"`}
                      placement={"left"}
                    >
                      <IconButton
                        edge="end"
                        aria-label="add filter"
                        onClick={() => handleAddFilterDialogOpen(stream)}
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
                {(filtersByStreamId[stream.id] ?? []).map((filter: any) => (
                  <ListItemButton
                    key={filter.id}
                    component={Link}
                    to={`/filter/${filter.id}`}
                  >
                    <ListItemText sx={{ pl: 2 }} primary={filter.name} />
                    {isAdmin(currentUser) && (
                      <ListItemSecondaryAction>
                        <Tooltip
                          title={`Delete filter "${filter.name}"`}
                          placement={"left"}
                        >
                          <Button
                            onClick={(e: any) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleDeleteFilter(filter.id);
                            }}
                            color="error"
                          >
                            <DeleteIcon />
                          </Button>
                        </Tooltip>
                      </ListItemSecondaryAction>
                    )}
                  </ListItemButton>
                ))}
              </List>
            </Fragment>
          ))}
        </List>
      </Paper>
      {currentUser.permissions.includes("System admin") && (
        <Button
          primary
          onClick={() => setAddStreamOpen(true)}
          disabled={group?.streams?.length >= streams.length}
        >
          Add stream
        </Button>
      )}
      <Dialog
        fullScreen={fullScreen}
        open={addStreamOpen}
        onClose={handleAddStreamClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit2(onSubmitAddStream)}>
          <DialogTitle id="responsive-dialog-title">
            Add Stream to group
          </DialogTitle>
          <DialogContent dividers>
            <FormControl required fullWidth>
              <InputLabel>Alert stream</InputLabel>
              <Controller
                name="stream_id"
                defaultValue={0}
                control={control2}
                rules={{ validate: isStreamIdInStreams }}
                render={({ field: { onChange, value } }) => (
                  <Select
                    label="Select stream"
                    labelId="alert-stream-select-required-label"
                    onChange={onChange}
                    value={value}
                  >
                    {streams?.map(
                      (stream: any) =>
                        // display only streams that are not yet added
                        !groupStreamIds?.includes(stream.id) && (
                          <MenuItem value={stream.id} key={stream.id}>
                            {stream.name}
                          </MenuItem>
                        ),
                    )}
                  </Select>
                )}
              />
              <FormHelperText>Required</FormHelperText>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button
              primary
              type="submit"
              data-testid="add-stream-dialog-submit"
            >
              Add
            </Button>
            <Button secondary autoFocus onClick={handleAddStreamClose}>
              Dismiss
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Dialog
        fullScreen={fullScreen}
        open={Boolean(filterStream)}
        onClose={handleAddFilterDialogClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit(onSubmitAddFilter)}>
          <DialogTitle id="responsive-dialog-title">
            {`Create a new filter for "${filterStream?.name}"`}
          </DialogTitle>
          <DialogContent dividers>
            <DialogContentText>
              Please refer to the &nbsp;
              <a
                href="https://fritz-marshal.org/doc/user_guide.html#alert-filters-in-fritz"
                target="_blank"
                rel="noreferrer"
              >
                docs <OpenInNewIcon style={{ fontSize: "small" }} />
              </a>
              &nbsp; for an extensive guide on Alert filters in Fritz.
            </DialogContentText>
            <Controller
              render={({ field: { onChange, value } }) => (
                <TextField
                  autoFocus
                  required
                  margin="dense"
                  name="filter_name"
                  label="Filter Name"
                  type="text"
                  fullWidth
                  inputRef={
                    register("filter_name", {
                      required: true,
                      minLength: 3,
                    }) as any
                  }
                  onChange={onChange}
                  value={value}
                />
              )}
              name="filter_name"
              control={control}
            />
          </DialogContent>
          <DialogActions>
            <Button
              primary
              type="submit"
              data-testid="add-filter-dialog-submit"
            >
              Add
            </Button>
            <Button secondary autoFocus onClick={handleAddFilterDialogClose}>
              Dismiss
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
};

export default GroupFiltersStreams;

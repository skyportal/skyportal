import React, { useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemSecondaryAction from "@mui/material/ListItemSecondaryAction";
import ListItemText from "@mui/material/ListItemText";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import useMediaQuery from "@mui/material/useMediaQuery";

import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormHelperText from "@mui/material/FormHelperText";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "../FormValidationError";
import Button from "../Button";

import * as filterActions from "../../ducks/filter";
import * as groupActions from "../../ducks/group";
import * as streamsActions from "../../ducks/streams";

const GroupFiltersStreams = ({ group, currentUser, isAdmin, theme }) => {
  const [addFilterDialogOpen, setAddFilterDialogOpen] = useState(false);
  const [addStreamOpen, setAddStreamOpen] = useState(false);
  const dispatch = useDispatch();
  const streams = useSelector((state) => state.streams);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm();
  const { handleSubmit: handleSubmit2, control: control2 } = useForm();
  const fullScreen = !useMediaQuery(theme.breakpoints.up("md"));

  if (!streams?.length) return null;

  const handleAddFilterDialogClose = () => {
    setAddFilterDialogOpen(false);
  };

  const handleAddStreamClose = () => {
    setAddStreamOpen(false);
  };

  // add filter to group
  const onSubmitAddFilter = async (data) => {
    const result = await dispatch(
      filterActions.addGroupFilter({
        name: data.filter_name,
        group_id: group.id,
        stream_id: data.filter_stream_id,
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification("Added filter to group"));
      dispatch(groupActions.fetchGroup(group.id));
      handleAddFilterDialogClose();
    }
  };

  // add stream to group
  const onSubmitAddStream = async (data) => {
    const result = await dispatch(
      streamsActions.addGroupStream({
        group_id: group.id,
        stream_id: data.stream_id,
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification("Added stream to group"));
      dispatch(groupActions.fetchGroup(group.id));
      setAddStreamOpen(false);
    }
  };

  const groupStreamIds = group?.streams?.map((stream) => stream.id);

  const isStreamIdInStreams = (sid) =>
    streams?.map((stream) => stream.id).includes(sid);

  return (
    <>
      <Accordion defaultExpanded>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel-streams-content"
          id="panel-streams-header"
        >
          <Typography variant="h6">Alert streams and filters</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            {group.streams?.map((stream) => (
              <ListItem key={stream.name}>
                <ListItemText primary={stream.name} />
                <List disablePadding>
                  {group.filters
                    ?.filter((f) => f.stream_id === stream.id)
                    .map((filter) => (
                      <ListItem key={filter.id}>
                        <Link to={`/filter/${filter.id}`}>
                          <ListItemText primary={filter.name} />
                        </Link>
                        {isAdmin(currentUser) && (
                          <ListItemSecondaryAction>
                            <IconButton
                              edge="end"
                              aria-label="delete"
                              onClick={async () => {
                                const result = await dispatch(
                                  filterActions.deleteGroupFilter({
                                    filter_id: filter.id,
                                  }),
                                );
                                if (result.status === "success") {
                                  dispatch(
                                    showNotification(
                                      "Deleted filter from group",
                                    ),
                                  );
                                }
                                dispatch(groupActions.fetchGroup(group.id));
                              }}
                              size="large"
                            >
                              <DeleteIcon />
                            </IconButton>
                          </ListItemSecondaryAction>
                        )}
                      </ListItem>
                    ))}
                </List>
              </ListItem>
            ))}
          </List>

          <div>
            {/* only Super admins can add streams to groups */}
            {currentUser.permissions.includes("System admin") &&
              streams?.length > 0 &&
              group?.streams?.length < streams?.length && (
                <Button
                  primary
                  onClick={() => setAddStreamOpen(true)}
                  style={{ marginRight: 10 }}
                >
                  Add stream
                </Button>
              )}

            {isAdmin(currentUser) && group?.streams?.length > 0 && (
              <Button primary onClick={() => setAddFilterDialogOpen(true)}>
                Add filter
              </Button>
            )}
          </div>
        </AccordionDetails>
      </Accordion>
      <Dialog
        fullScreen={fullScreen}
        open={addStreamOpen}
        onClose={handleAddStreamClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit2(onSubmitAddStream)}>
          <DialogTitle id="responsive-dialog-title">
            Add alert stream to group
          </DialogTitle>
          <DialogContent dividers>
            <FormControl required fullWidth>
              <InputLabel>Alert stream</InputLabel>
              <Controller
                label="Alert stream"
                name="stream_id"
                defaultValue={0}
                control={control2}
                rules={{ validate: isStreamIdInStreams }}
                render={({ field: { onChange, value } }) => (
                  <Select
                    labelId="alert-stream-select-required-label"
                    onChange={onChange}
                    value={value}
                  >
                    {streams?.map(
                      (stream) =>
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
        open={addFilterDialogOpen}
        onClose={handleAddFilterDialogClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit(onSubmitAddFilter)}>
          <DialogTitle id="responsive-dialog-title">
            Create a new alert stream filter
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
                  inputRef={register("filter_name", {
                    required: true,
                    minLength: 3,
                  })}
                  onChange={onChange}
                  value={value}
                />
              )}
              name="filter_name"
              control={control}
            />
            <FormControl required fullWidth>
              <InputLabel>Alert stream</InputLabel>
              {errors.filter_stream_id && (
                <FormValidationError
                  message={errors.filter_stream_id.message}
                />
              )}
              <Controller
                name="filter_stream_id"
                defaultValue={0}
                control={control}
                rules={{ validate: isStreamIdInStreams }}
                render={({ field: { onChange, value } }) => (
                  <Select
                    labelId="alert-stream-select-required-label"
                    onChange={onChange}
                    value={value}
                  >
                    {group.streams?.map((stream) => (
                      <MenuItem key={stream.id} value={stream.id}>
                        {stream.name}
                      </MenuItem>
                    ))}
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
    </>
  );
};

GroupFiltersStreams.propTypes = {
  group: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    nickname: PropTypes.string,
    users: PropTypes.arrayOf(
      PropTypes.shape({
        username: PropTypes.string,
        id: PropTypes.number,
        first_name: PropTypes.string,
        last_name: PropTypes.string,
      }),
    ),
    streams: PropTypes.arrayOf(PropTypes.shape()).isRequired,
    filters: PropTypes.arrayOf(PropTypes.shape()).isRequired,
  }).isRequired,
  theme: PropTypes.shape().isRequired,
  currentUser: PropTypes.shape({
    username: PropTypes.string,
    id: PropTypes.number,
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    permissions: PropTypes.arrayOf(PropTypes.string),
    roles: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  isAdmin: PropTypes.func.isRequired,
};

export default GroupFiltersStreams;

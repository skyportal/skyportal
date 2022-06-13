import React, { useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";
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
import Button from "@mui/material/Button";
import useMediaQuery from "@mui/material/useMediaQuery";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormHelperText from "@mui/material/FormHelperText";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import { showNotification } from "baselayer/components/Notifications";

import * as filterActions from "../ducks/filter";
import * as groupActions from "../ducks/group";
import * as streamsActions from "../ducks/streams";

const GroupFiltersStreams = ({
  group,
  classes,
  currentUser,
  isAdmin,
  theme,
}) => {
  const [addFilterDialogOpen, setAddFilterDialogOpen] = useState(false);
  const [addStreamOpen, setAddStreamOpen] = useState(false);
  const [panelStreamsExpanded, setPanelStreamsExpanded] =
    useState("panel-streams");
  const dispatch = useDispatch();
  const streams = useSelector((state) => state.streams);

  const { register, handleSubmit, control } = useForm();
  const fullScreen = !useMediaQuery(theme.breakpoints.up("md"));

  const handleAddFilterDialogClose = () => {
    setAddFilterDialogOpen(false);
  };

  const handleAddFilterDialogOpen = () => {
    setAddFilterDialogOpen(true);
  };

  const handleAddStreamOpen = () => {
    setAddStreamOpen(true);
  };

  const handleAddStreamClose = () => {
    setAddStreamOpen(false);
  };
  const handlePanelStreamsChange = (panel) => (event, isExpanded) => {
    setPanelStreamsExpanded(isExpanded ? panel : false);
  };

  // add filter to group
  const onSubmitAddFilter = async (data) => {
    const result = await dispatch(
      filterActions.addGroupFilter({
        name: data.filter_name,
        group_id: group.id,
        stream_id: data.filter_stream_id,
      })
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
      })
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
      {streams?.length > 0 && (
        <Accordion
          expanded={panelStreamsExpanded === "panel-streams"}
          onChange={handlePanelStreamsChange("panel-streams")}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="panel-streams-content"
            id="panel-streams-header"
            style={{ borderBottom: "1px solid rgba(0, 0, 0, .125)" }}
          >
            <Typography className={classes.heading}>
              Alert streams and filters
            </Typography>
          </AccordionSummary>
          <AccordionDetails className={classes.accordion_details}>
            <List component="nav" className={classes.padding_bottom}>
              {group.streams?.map((stream) => (
                <div key={stream.name}>
                  <ListItem key={stream.name}>
                    <ListItemText primary={stream.name} />
                  </ListItem>
                  <List component="nav" disablePadding>
                    {group.filters?.map((filter) =>
                      filter.stream_id === stream.id ? (
                        <ListItem button key={filter.id}>
                          <Link
                            to={`/filter/${filter.id}`}
                            className={classes.filterLink}
                          >
                            <ListItemText
                              key={filter.id}
                              className={classes.nested}
                              primary={filter.name}
                            />
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
                                    })
                                  );
                                  if (result.status === "success") {
                                    dispatch(
                                      showNotification(
                                        "Deleted filter from group"
                                      )
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
                      ) : (
                        ""
                      )
                    )}
                  </List>
                </div>
              ))}
            </List>

            <div>
              {/* only Super admins can add streams to groups */}
              {currentUser.permissions.includes("System admin") &&
                streams?.length > 0 &&
                group?.streams?.length < streams?.length && (
                  <Button
                    variant="contained"
                    color="primary"
                    className={classes.button_add}
                    onClick={handleAddStreamOpen}
                    style={{ marginRight: 10 }}
                  >
                    Add stream
                  </Button>
                )}

              {isAdmin(currentUser) && group?.streams?.length > 0 && (
                <Button
                  variant="contained"
                  color="primary"
                  className={classes.button_add}
                  onClick={handleAddFilterDialogOpen}
                >
                  Add filter
                </Button>
              )}
            </div>
          </AccordionDetails>
        </Accordion>
      )}
      <Dialog
        fullScreen={fullScreen}
        open={addStreamOpen}
        onClose={handleAddStreamClose}
        aria-labelledby="responsive-dialog-title"
      >
        <form onSubmit={handleSubmit(onSubmitAddStream)}>
          <DialogTitle id="responsive-dialog-title">
            Add alert stream to group
          </DialogTitle>
          <DialogContent dividers>
            <FormControl required className={classes.selectEmpty}>
              <InputLabel name="alert-stream-select-required-label">
                Alert stream
              </InputLabel>
              <Controller
                labelId="alert-stream-select-required-label"
                name="stream_id"
                as={Select}
                defaultValue={0}
                control={control}
                rules={{ validate: isStreamIdInStreams }}
              >
                {streams?.map(
                  (stream) =>
                    // display only streams that are not yet added
                    !groupStreamIds?.includes(stream.id) && (
                      <MenuItem value={stream.id} key={stream.id}>
                        {stream.name}
                      </MenuItem>
                    )
                )}
              </Controller>
              <FormHelperText>Required</FormHelperText>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              className={classes.button_add}
              data-testid="add-stream-dialog-submit"
            >
              Add
            </Button>
            <Button autoFocus onClick={handleAddStreamClose} color="primary">
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
            <TextField
              autoFocus
              required
              margin="dense"
              name="filter_name"
              label="Filter Name"
              type="text"
              fullWidth
              inputRef={register({ required: true, minLength: 3 })}
            />
            <FormControl required className={classes.selectEmpty}>
              <InputLabel name="alert-stream-select-required-label">
                Alert stream
              </InputLabel>
              <Controller
                labelId="alert-stream-select-required-label"
                name="filter_stream_id"
                as={Select}
                defaultValue={0}
                control={control}
                rules={{ validate: isStreamIdInStreams }}
              >
                {group.streams?.map((stream) => (
                  <MenuItem key={stream.id} value={stream.id}>
                    {stream.name}
                  </MenuItem>
                ))}
              </Controller>
              <FormHelperText>Required</FormHelperText>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button
              variant="contained"
              color="primary"
              className={classes.button_add}
              type="submit"
              data-testid="add-filter-dialog-submit"
            >
              Add
            </Button>
            <Button
              autoFocus
              onClick={handleAddFilterDialogClose}
              color="primary"
            >
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
      })
    ),
    streams: PropTypes.arrayOf(PropTypes.shape()).isRequired,
    filters: PropTypes.arrayOf(PropTypes.shape()).isRequired,
  }).isRequired,
  classes: PropTypes.shape().isRequired,
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

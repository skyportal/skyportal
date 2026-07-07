import { useState } from "react";
import { Link } from "react-router-dom";
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
import ListItemButton from "@mui/material/ListItemButton";
import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "../FormValidationError";
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
  classes: any;
  currentUser: any;
  isAdmin: (...args: any[]) => any;
  theme: any;
}

const GroupFiltersStreams = ({
  group,
  classes,
  currentUser,
  isAdmin,
  theme,
}: GroupFiltersStreamsProps) => {
  const [addFilterDialogOpen, setAddFilterDialogOpen] = useState(false);
  const [addStreamOpen, setAddStreamOpen] = useState(false);
  const [panelStreamsExpanded, setPanelStreamsExpanded] =
    useState<any>("panel-streams");
  const dispatch = useAppDispatch();
  const { data: streams } = useGetStreamsQuery();
  const [addGroupFilter] = useAddGroupFilterMutation();
  const [deleteGroupFilter] = useDeleteGroupFilterMutation();
  const [addGroupStream] = useAddGroupStreamMutation();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm();

  const { handleSubmit: handleSubmit2, control: control2 } = useForm();

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
  const handlePanelStreamsChange =
    (panel: any) => (_event: any, isExpanded: any) => {
      setPanelStreamsExpanded(isExpanded ? panel : false);
    };

  // add filter to group
  const onSubmitAddFilter = async (data: any) => {
    try {
      await addGroupFilter({
        name: data.filter_name,
        group_id: group.id,
        stream_id: data.filter_stream_id,
      }).unwrap();
      dispatch(showNotification("Added filter to group"));
      dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));
      handleAddFilterDialogClose();
    } catch {
      // error notification handled by the base query
    }
  };

  // add stream to group
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

  return (
    <>
      {(streams?.length ?? 0) > 0 && (
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
            <Typography variant="h6">Alert streams and filters</Typography>
          </AccordionSummary>
          <AccordionDetails className={classes.accordion_details}>
            <List component="nav" className={classes.padding_bottom}>
              {group.streams?.map((stream: any) => (
                <div key={stream.name}>
                  <ListItem key={stream.name}>
                    <ListItemText primary={stream.name} />
                  </ListItem>
                  <List component="nav" disablePadding>
                    {group.filters
                      ?.filter((f: any) => f.stream_id === stream.id)
                      .map((filter: any) => (
                        <ListItemButton
                          key={filter.id}
                          component={Link}
                          to={`/filter/${filter.id}`}
                        >
                          <ListItemText
                            key={filter.id}
                            className={classes.nested}
                            primary={filter.name}
                          />
                          {isAdmin(currentUser) && (
                            <ListItemSecondaryAction>
                              <IconButton
                                edge="end"
                                aria-label="delete"
                                onClick={async () => {
                                  try {
                                    await deleteGroupFilter({
                                      filter_id: filter.id,
                                    }).unwrap();
                                    dispatch(
                                      showNotification(
                                        "Deleted filter from group",
                                      ),
                                    );
                                  } catch {
                                    // error notification handled by the base query
                                  }
                                  dispatch(
                                    groupApi.util.invalidateTags([
                                      { type: "Group", id: group.id },
                                    ]),
                                  );
                                }}
                                size="large"
                              >
                                <DeleteIcon />
                              </IconButton>
                            </ListItemSecondaryAction>
                          )}
                        </ListItemButton>
                      ))}
                  </List>
                </div>
              ))}
            </List>

            <div>
              {/* only Super admins can add streams to groups */}
              {currentUser.permissions.includes("System admin") &&
                (streams?.length ?? 0) > 0 &&
                (group?.streams?.length ?? 0) < (streams?.length ?? 0) && (
                  <Button
                    primary
                    className={classes.button_add}
                    onClick={handleAddStreamOpen}
                    style={{ marginRight: 10 }}
                  >
                    Add stream
                  </Button>
                )}

              {isAdmin(currentUser) && group?.streams?.length > 0 && (
                <Button
                  primary
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
        <form onSubmit={handleSubmit2(onSubmitAddStream)}>
          <DialogTitle id="responsive-dialog-title">
            Add alert stream to group
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
              className={classes.button_add}
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
            <FormControl required fullWidth>
              <InputLabel>Alert stream</InputLabel>
              {errors["filter_stream_id"] && (
                <FormValidationError
                  message={errors["filter_stream_id"].message as any}
                />
              )}
              <Controller
                name="filter_stream_id"
                defaultValue={0}
                control={control}
                rules={{ validate: isStreamIdInStreams }}
                render={({ field: { onChange, value } }) => (
                  <Select
                    label="Alert stream"
                    labelId="alert-stream-select-required-label"
                    onChange={onChange}
                    value={value}
                  >
                    {group.streams?.map((stream: any) => (
                      <MenuItem key={stream.id} value={stream.id}>
                        {stream.name}
                      </MenuItem>
                    ))}
                  </Select>
                )}
              />
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button
              primary
              className={classes.button_add}
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

export default GroupFiltersStreams;

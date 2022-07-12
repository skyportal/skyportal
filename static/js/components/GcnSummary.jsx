import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { withStyles, makeStyles } from "@mui/styles";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import grey from "@mui/material/colors/grey";
import TextField from "@mui/material/TextField";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import LoadingButton from "@mui/lab/LoadingButton";
import GetApp from "@mui/icons-material/GetApp";

import { showNotification } from "baselayer/components/Notifications";
import {
  SelectLabelWithChips,
  SelectSingleLabelWithChips,
} from "./SelectWithChips";
import * as usersActions from "../ducks/users";
import * as groupsActions from "../ducks/groups";
import { getGcnEventSummary } from "../ducks/gcnEvent";

const useStyles = makeStyles((theme) => ({
  shortcutButtons: {
    margin: "1rem 0",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    padding: theme.spacing(1),
    alignItems: "left",
    justifyContent: "left",
    height: "100%",
    width: "100%",
    " & > *": {
      marginTop: theme.spacing(2),
      marginBottom: theme.spacing(2),
    },
  },
  content: {
    height: "100%",
    width: "100%",
  },
  textForm: {
    height: "100%",
    width: "100%",
    overflow: "hidden",
  },
  textField: {
    height: "80vh",
    width: "100%",
    overflow: "auto",
  },
  checkboxes: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gridGap: "1rem",
    width: "100%",
    height: "100%",
  },
  button: {
    width: "100%",
  },
  buttons: {
    display: "flex",
    flexDirection: "row",
    width: "100%",
    gap: theme.spacing(2),
  },
}));

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle disableTypography className={classes.root}>
      <Typography variant="h6" className={classes.title}>
        {children}
      </Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
);

const GcnSummary = ({ dateobs }) => {
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.userAccessible);
  const { users } = useSelector((state) => state.users);
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [dataFetched, setDataFetched] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const { summary } = useSelector((state) => state.gcnEvent);
  const [text, setText] = useState("");
  const [nb, setNb] = useState("");
  const [title, setTitle] = useState("Gcn Summary");
  const [subject, setSubject] = useState(`Follow-up on GCN Event ...`);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [localizationCumprob, setLocalizationCumprob] = useState("0.95");
  const [showSources, setShowSources] = useState(false);
  const [showGalaxies, setShowGalaxies] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [noText, setNoText] = useState(false);

  const [fetching, setFetching] = useState(false);

  const groups_list = groups.map((group) => ({
    id: group.id,
    label: group.name,
  }));

  const users_list = users?.map((user) => ({
    id: user.id,
    label: `${user.first_name} ${user.last_name}`,
  }));

  useEffect(() => {
    const fetchData = () => {
      dispatch(usersActions.fetchUsers());
      dispatch(groupsActions.fetchGroups());
    };
    if (!dataFetched) {
      fetchData();
      setDataFetched(true);
    } else if (summary) {
      if (summary?.length === 0) {
        dispatch(
          showNotification("No data found with these parameters", "warning")
        );
      }
      setText(summary.join(""));
      setFetching(false);
    }
    const default_start_date = new Date(dateobs).toISOString();
    let default_end_date = new Date(dateobs);
    default_end_date.setDate(default_end_date.getDate() + 7);
    default_end_date = default_end_date.toISOString();
    setStartDate(default_start_date.slice(0, 19));
    setEndDate(default_end_date.slice(0, 19));
    setSubject(`Follow-up on GCN Event ${dateobs}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateobs, summary, dataFetched, dispatch]);

  const handleClose = () => {
    setOpen(false);
  };

  const onUserSelectChange = (event) => {
    let new_selected_users = [];
    event.target.value.forEach((user) => {
      if (
        !new_selected_users.some(
          (selected_user) => selected_user.id === user.id
        )
      ) {
        new_selected_users.push(user);
      } else {
        // remove the user from the list
        new_selected_users = new_selected_users.filter(
          (selected_user) => selected_user.id !== user.id
        );
      }
    });
    setSelectedUsers(new_selected_users);
  };

  const onGroupSelectChange = (event) => {
    setSelectedGroup(event.target.value);
  };

  const validateSubmit = () => {
    let valid = true;

    if (!noText) {
      if (title === "") {
        dispatch(
          showNotification(
            "Please enter a title when noText is not checked",
            "error"
          )
        );
        valid = false;
      }
      if (subject === "") {
        dispatch(
          showNotification(
            "Please enter a subject when noText is not checked",
            "error"
          )
        );
        valid = false;
      }
      if (!selectedGroup?.id) {
        dispatch(
          showNotification(
            "Please select a group when noText is not checked",
            "error"
          )
        );
        valid = false;
      }
    }
    if (!startDate) {
      dispatch(showNotification("Please select a start date", "error"));
      valid = false;
    }
    if (!endDate) {
      dispatch(showNotification("Please select an end date", "error"));
      valid = false;
    }
    if (!showSources && !showGalaxies && !showObservations) {
      dispatch(
        showNotification(
          "Please select at least one type to show: sources, galaxies or observations",
          "error"
        )
      );
      valid = false;
    }
    return valid;
  };

  const handleSubmitGcnSummary = async () => {
    if (validateSubmit()) {
      const params = {
        title,
        subject,
        userIds: selectedUsers.map((user) => user.id),
        groupId: selectedGroup?.id,
        startDate,
        endDate,
        localizationCumprob,
        showSources,
        showGalaxies,
        showObservations,
        noText,
      };
      if (nb !== "") {
        params.number = nb;
      }
      setFetching(true);
      dispatch(getGcnEventSummary({ dateobs, params })).then((response) => {
        if (response.status !== "success") {
          setFetching(false);
        }
      });
    }
  };

  return (
    <>
      <Button
        variant="outlined"
        name="gcn_summary"
        onClick={() => setOpen(true)}
      >
        Summary
      </Button>
      {open && dataFetched && (
        <Dialog
          open={open}
          onClose={handleClose}
          style={{ position: "fixed" }}
          fullScreen
        >
          <DialogTitle onClose={handleClose}>Event {dateobs}</DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={3}>
              <Grid item md={4} sm={12}>
                <Paper elevation={1} className={classes.form}>
                  <TextField
                    id="title"
                    label="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                  <TextField
                    id="subject"
                    label="Subject"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                  />
                  <TextField
                    id="number"
                    label="Number (Optional)"
                    value={nb}
                    onChange={(e) => setNb(e.target.value)}
                  />
                  <SelectSingleLabelWithChips
                    label="Group"
                    id="group-select"
                    initValue={selectedGroup}
                    onChange={onGroupSelectChange}
                    options={groups_list}
                  />
                  <SelectLabelWithChips
                    label="Users (Optional)"
                    id="users-select"
                    initValue={selectedUsers}
                    onChange={onUserSelectChange}
                    options={users_list}
                  />
                  <TextField
                    id="startDate"
                    label="Start Date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                  <TextField
                    id="endDate"
                    label="End Date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                  <TextField
                    id="localizationCumprob"
                    label="Localization Cumprob"
                    value={localizationCumprob}
                    onChange={(e) => setLocalizationCumprob(e.target.value)}
                  />
                  <div className={classes.checkboxes}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          label="Show Sources"
                          checked={showSources}
                          onChange={(e) => setShowSources(e.target.checked)}
                        />
                      }
                      label="Show Sources"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          label="Show Galaxies"
                          checked={showGalaxies}
                          onChange={(e) => setShowGalaxies(e.target.checked)}
                        />
                      }
                      label="Show Galaxies"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          label="Show Observations"
                          checked={showObservations}
                          onChange={(e) =>
                            setShowObservations(e.target.checked)
                          }
                        />
                      }
                      label="Show Observations"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          label="No Text"
                          checked={noText}
                          onChange={(e) => setNoText(e.target.checked)}
                        />
                      }
                      label="No Text"
                    />
                  </div>
                  <div className={classes.buttons}>
                    <LoadingButton
                      onClick={() => handleSubmitGcnSummary()}
                      loading={fetching}
                      loadingPosition="end"
                      variant="contained"
                      className={classes.button}
                    >
                      Get Summary
                    </LoadingButton>
                    <Button
                      startIcon={<GetApp />}
                      disabled={!summary || summary?.length === 0}
                      onClick={() => {
                        const blob = new Blob([text], { type: "text/plain" });
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = `${title}_${dateobs}.txt`;
                        link.click();
                      }}
                      variant="contained"
                      className={classes.button}
                    >
                      Download
                    </Button>
                  </div>
                </Paper>
              </Grid>
              <Grid item md={8} sm={12}>
                <Paper elevation={1} className={classes.content}>
                  {fetching && (
                    <div
                      style={{
                        display: "flex",
                        width: "100%",
                        height: "100%",
                        justifyContent: "center",
                        alignItems: "center",
                      }}
                    >
                      <CircularProgress />
                    </div>
                  )}
                  {!fetching && text && (
                    <TextField
                      id="text"
                      label="Text"
                      multiline
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      className={classes.textField}
                      InputProps={{
                        style: {
                          fontSize: "0.9rem",
                          fontFamily: "monospace",
                        },
                      }}
                    />
                  )}
                  {!fetching && !text && (
                    <div
                      style={{
                        textAlign: "center",
                        display: "flex",
                        width: "100%",
                        height: "100%",
                        justifyContent: "center",
                        alignItems: "center",
                      }}
                    >
                      <Typography variant="h4">
                        Use the form on the left to generate a summary.
                      </Typography>
                    </div>
                  )}
                </Paper>
              </Grid>
            </Grid>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};

GcnSummary.propTypes = {
  dateobs: PropTypes.string.isRequired,
};

export default GcnSummary;

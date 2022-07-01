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
import { SelectLabelWithChips } from "./SelectWithChips";
import * as usersActions from "../ducks/users";
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

const GcnSummary = ({ gcnEvent }) => {
  const classes = useStyles();
  const { users } = useSelector((state) => state.users);
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [dataFetched, setDataFetched] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const { summary } = useSelector((state) => state.gcnEvent);

  const default_start_date = new Date(gcnEvent?.dateobs).toISOString();
  let default_end_date = new Date(gcnEvent?.dateobs);
  default_end_date.setDate(default_end_date.getDate() + 7);
  default_end_date = default_end_date.toISOString();
  const [text, setText] = useState("");
  const [title, setTitle] = useState("Gcn Summary");
  const [subject, setSubject] = useState("Follow-up on GCN Event");
  const [startDate, setStartDate] = useState(default_start_date.slice(0, 19));
  const [endDate, setEndDate] = useState(default_end_date.slice(0, 19));
  const [localizationCumprob, setLocalizationCumprob] = useState("0.95");
  const [showSources, setShowSources] = useState(false);
  const [showGalaxies, setShowGalaxies] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [noText, setNoText] = useState(false);

  const [fetching, setFetching] = useState(false);

  const users_list = users?.map((user) => ({
    id: user.id,
    label: `${user.first_name} ${user.last_name}`,
  }));

  useEffect(() => {
    const fetchData = () => {
      dispatch(usersActions.fetchUsers());
    };
    if (!dataFetched) {
      fetchData();
      setDataFetched(true);
    } else if (summary) {
      setText(summary.join(""));
      setFetching(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary, dataFetched, dispatch]);

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

  const handleSubmitGcnSummary = async () => {
    const dateobs = gcnEvent?.dateobs;
    const params = {
      title,
      subject,
      userIds: selectedUsers.map((user) => user.id),
      group_id: 1,
      startDate,
      endDate,
      localizationCumprob,
      showSources,
      showGalaxies,
      showObservations,
      noText,
    };
    setFetching(true);
    dispatch(getGcnEventSummary({ dateobs, params })).then((response) => {
      if (response.status !== "success") {
        setFetching(false);
      }
    });
  };

  return (
    <div>
      <Button
        variant="contained"
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
          <DialogTitle onClose={handleClose}>
            Event {gcnEvent?.dateobs}
          </DialogTitle>
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
                  <SelectLabelWithChips
                    label="Users"
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
                        checked={showObservations}
                        onChange={(e) => setShowObservations(e.target.checked)}
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
                  <LoadingButton
                    onClick={() => handleSubmitGcnSummary()}
                    loading={fetching}
                    loadingPosition="end"
                    variant="contained"
                  >
                    Get Summary
                  </LoadingButton>
                  <Button
                    startIcon={<GetApp />}
                    onClick={() => {
                      const blob = new Blob([text], { type: "text/plain" });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement("a");
                      link.href = url;
                      link.download = `${title}_${gcnEvent?.dateobs}.txt`;
                      link.click();
                    }}
                  />
                </Paper>
              </Grid>
              <Grid item md={8} sm={12}>
                <Paper elevation={1} className={classes.content}>
                  {fetching && <CircularProgress />}
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
                          fontSize: "1rem",
                          fontFamily: "monospace",
                        },
                      }}
                    />
                  )}
                </Paper>
              </Grid>
            </Grid>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

GcnSummary.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    id: PropTypes.number,
  }).isRequired,
};

export default GcnSummary;

import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { makeStyles, withStyles } from "@mui/styles";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import grey from "@mui/material/colors/grey";
import TextField from "@mui/material/TextField";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Checkbox from "@mui/material/Checkbox";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import LoadingButton from "@mui/lab/LoadingButton";
import GetApp from "@mui/icons-material/GetApp";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { showNotification } from "baselayer/components/Notifications";
import {
  SelectLabelWithChips,
  SelectSingleLabelWithChips,
} from "../SelectWithChips";

import { fetchGroup } from "../../ducks/group";
import { fetchGroups } from "../../ducks/groups";
import { fetchInstruments } from "../../ducks/instruments";
import {
  deleteGcnEventSummary,
  fetchGcnEventSummary,
  patchGcnEventSummary,
  postGcnEventSummary,
} from "../../ducks/gcnEvent";
import Button from "../Button";
import GcnSummaryTable from "./GcnSummaryTable";

dayjs.extend(relativeTime);
dayjs.extend(utc);

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
  menu: {
    display: "flex",
    direction: "row",
    justifyContent: "space-around",
    alignItems: "center",
    marginBottom: "1rem",
  },
  select: {
    width: "100%",
  },
  listItem: {
    whiteSpace: "normal",
    maxWidth: "30vw",
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
  ),
);

const GcnSummary = ({ dateobs }) => {
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.userAccessible);
  const users = useSelector((state) => state.group?.users);
  const { instrumentList } = useSelector((state) => state.instruments);
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const [text, setText] = useState("");
  const [nb, setNb] = useState("");
  const [title, setTitle] = useState("Gcn Summary");
  const [subject, setSubject] = useState(`Follow-up on GCN Event ...`);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [localizationName, setLocalizationName] = useState(null);
  const [localizationCumprob, setLocalizationCumprob] = useState("0.95");
  const [numberDetections, setNumberDetections] = useState("2");
  const [numberObservations, setNumberObservations] = useState("1");
  const [showSources, setShowSources] = useState(false);
  const [showGalaxies, setShowGalaxies] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [noText, setNoText] = useState(false);
  const [photometryInWindow, setPhotometryInWindow] = useState(false);
  const [selectedGcnSummaryId, setSelectedGcnSummaryId] = useState(null);
  const [selectedInstruments, setSelectedInstruments] = useState([]);
  const [selectedAcknowledgement, setSelectedAcknowledgement] = useState(null);

  const gcnSummaryAcknowledgements = useSelector(
    (state) => state.config.gcnSummaryAcknowledgements,
  );

  const acknowledgmentOptions = selectedAcknowledgement
    ? ["Clear selection", ...gcnSummaryAcknowledgements]
    : gcnSummaryAcknowledgements;

  const [loading, setLoading] = useState(false);

  const [displayList, setDisplayList] = useState(true);

  const groups_list = groups.map((group) => ({
    id: group.id,
    label: group.name,
  }));

  const users_list = users?.map((user) => ({
    id: user.id,
    label: `${user.first_name} ${user.last_name}`,
  }));

  let sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  // to each sortedInstrument, add a label field with the instrument name
  sortedInstrumentList = sortedInstrumentList.map((instrument) => ({
    ...instrument,
    label: instrument.name,
  }));

  useEffect(() => {
    if (instrumentList?.length === 0) {
      dispatch(fetchInstruments());
    }
  }, []);

  useEffect(() => {
    const fetchSummary = (summaryID) => {
      dispatch(fetchGcnEventSummary({ dateobs, summaryID })).then(
        (response) => {
          if (response.status === "success") {
            setText(response.data.text);
          } else {
            setText("");
            dispatch(showNotification("Error fetching summary", "error"));
          }
        },
      );
    };
    if (gcnEvent?.summaries?.length > 0) {
      if (selectedGcnSummaryId) {
        fetchSummary(selectedGcnSummaryId);
        setDisplayList(false);
      } else {
        setText("");
      }
    }
  }, [gcnEvent, selectedGcnSummaryId]);

  useEffect(() => {
    if (!groups && open) {
      dispatch(fetchGroups());
    }
    const defaultStartDate = dayjs.utc(dateobs).format("YYYY-MM-DD HH:mm:ss");
    const defaultEndDate = dayjs
      .utc(dateobs)
      .add(7, "day")
      .format("YYYY-MM-DD HH:mm:ss");
    setStartDate(defaultStartDate);
    setEndDate(defaultEndDate);
    setSubject(`Follow-up on GCN Event ${dateobs}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateobs, dispatch]);

  useEffect(() => {
    if (selectedGroup?.id) {
      dispatch(fetchGroup(selectedGroup?.id));
    }
  }, [dispatch, selectedGroup]);

  useEffect(() => {
    if (gcnEvent?.localizations?.length > 0) {
      setLocalizationName(gcnEvent?.localizations[0]?.localization_name);
    }
  }, [gcnEvent]);

  const handleClose = () => {
    setOpen(false);
  };

  const onAcknowledgementSelectChange = (event) => {
    if (event.target.value === "Clear selection") {
      setSelectedAcknowledgement(null);
    } else {
      setSelectedAcknowledgement(event.target.value);
    }
  };

  const onUserSelectChange = (event) => {
    let new_selected_users = [];
    event.target.value.forEach((user) => {
      if (
        !new_selected_users.some(
          (selected_user) => selected_user.id === user.id,
        )
      ) {
        new_selected_users.push(user);
      } else {
        // remove the user from the list
        new_selected_users = new_selected_users.filter(
          (selected_user) => selected_user.id !== user.id,
        );
      }
    });
    setSelectedUsers(new_selected_users);
  };

  const onGroupSelectChange = (event) => {
    setSelectedGroup(event.target.value);
  };

  const onInstrumentSelectChange = (event) => {
    let new_selected_instruments = [];
    event.target.value.forEach((instrument) => {
      if (
        !new_selected_instruments.some(
          (selected_instrument) => selected_instrument.id === instrument.id,
        )
      ) {
        new_selected_instruments.push(instrument);
      } else {
        // remove the user from the list
        new_selected_instruments = new_selected_instruments.filter(
          (selected_instrument) => selected_instrument.id !== instrument.id,
        );
      }
    });
    setSelectedInstruments(new_selected_instruments);
  };

  const validateSubmit = () => {
    let valid = true;

    if (!noText) {
      if (title === "") {
        dispatch(showNotification("Please enter a title", "error"));
        valid = false;
      }
      if (subject === "") {
        dispatch(
          showNotification(
            "Please enter a subject when noText is not checked",
            "error",
          ),
        );
        valid = false;
      }
      if (!selectedGroup?.id) {
        dispatch(showNotification("Please select a group", "error"));
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
          "error",
        ),
      );
      valid = false;
    }
    return valid;
  };

  const handleSubmitGcnSummary = async () => {
    if (validateSubmit()) {
      setLoading(true);
      const params = {
        title,
        subject,
        userIds: selectedUsers.map((user) => user.id),
        groupId: selectedGroup?.id,
        startDate,
        endDate,
        localizationName,
        localizationCumprob,
        numberDetections,
        numberObservations,
        showSources,
        showGalaxies,
        showObservations,
        noText,
        photometryInWindow,
        instrumentIds: selectedInstruments.map((instrument) => instrument.id),
      };
      if (nb !== "") {
        params.number = nb;
      }
      if (selectedAcknowledgement !== null) {
        params.acknowledgements = selectedAcknowledgement;
      }
      if (params.instrumentIds?.length === 0) {
        delete params.instrumentIds;
      }
      dispatch(postGcnEventSummary({ dateobs, params })).then((response) => {
        if (response.status === "success") {
          dispatch(showNotification("Summary is being generated, please wait"));
        } else {
          dispatch(showNotification("Error generating summary", "error"));
        }
        setLoading(false);
      });
    }
  };

  const handleDeleteGcnEventSummary = (summaryID) => {
    dispatch(deleteGcnEventSummary({ dateobs, summaryID })).then((response) => {
      if (response.status === "success") {
        setSelectedGcnSummaryId(null);
        dispatch(showNotification("Summary deleted"));
      } else {
        dispatch(showNotification("Error deleting summary", "error"));
      }
    });
  };

  const handleSaveGcnSummary = () => {
    setLoading(true);
    const res = {
      body: text,
    };
    dispatch(patchGcnEventSummary(dateobs, selectedGcnSummaryId, res)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(showNotification("Summary saved"));
        } else {
          dispatch(showNotification("Error saving summary", "error"));
        }
      },
    );
    setLoading(false);
  };

  return (
    <>
      <Button secondary name="gcn_summary" onClick={() => setOpen(true)}>
        Summary
      </Button>
      {open && (
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
                  <SelectLabelWithChips
                    label="Instruments (Optional)"
                    id="instruments-select"
                    initValue={selectedInstruments}
                    onChange={onInstrumentSelectChange}
                    options={sortedInstrumentList}
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
                  <div>
                    <InputLabel id="localizationSelectLabel">
                      Localization Name
                    </InputLabel>
                    <Select
                      inputProps={{ MenuProps: { disableScrollLock: true } }}
                      labelId="localizationSelectLabel"
                      value={localizationName || ""}
                      onChange={(e) => setLocalizationName(e.target.value)}
                      name="gcnSummaryLocalizationSelect"
                      className={classes.select}
                    >
                      {gcnEvent.localizations?.map((localization) => (
                        <MenuItem
                          value={localization.localization_name}
                          key={localization.localization_name}
                        >
                          {`${localization.localization_name}`}
                        </MenuItem>
                      ))}
                    </Select>
                  </div>
                  <TextField
                    id="localizationCumprob"
                    label="Localization Cumulative Probability"
                    value={localizationCumprob}
                    onChange={(e) => setLocalizationCumprob(e.target.value)}
                  />
                  <TextField
                    id="numberDetections"
                    label="Minimum Number of Detections"
                    value={numberDetections}
                    onChange={(e) => setNumberDetections(e.target.value)}
                  />
                  <TextField
                    id="numberObservations"
                    label="Minimum Number of Observations (per field)"
                    value={numberObservations}
                    onChange={(e) => setNumberObservations(e.target.value)}
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
                          label="Table(s) Only"
                          checked={noText}
                          onChange={(e) => setNoText(e.target.checked)}
                        />
                      }
                      label="Table(s) Only"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          label="Photometry in Window (only between start and end dates)"
                          checked={photometryInWindow}
                          onChange={(e) =>
                            setPhotometryInWindow(e.target.checked)
                          }
                        />
                      }
                      label="Photometry in Window (only between start and end dates)"
                    />
                  </div>
                  <div>
                    <InputLabel id="acknowledgmentSelectLabel">
                      Acknowledgement
                    </InputLabel>
                    <Select
                      inputProps={{ MenuProps: { disableScrollLock: true } }}
                      labelId="acknowledgmentSelectLabel"
                      value={selectedAcknowledgement || ""}
                      onChange={(e) => onAcknowledgementSelectChange(e)}
                      name="gcnSummaryAcknowledgementSelect"
                      className={classes.select}
                    >
                      {acknowledgmentOptions?.map((acknowledgment) => (
                        <MenuItem
                          value={acknowledgment}
                          key={acknowledgment}
                          className={classes.listItem}
                        >
                          {`${acknowledgment}`}
                        </MenuItem>
                      ))}
                    </Select>
                  </div>
                  <div className={classes.buttons}>
                    <LoadingButton
                      onClick={() => handleSubmitGcnSummary()}
                      loading={loading}
                      loadingPosition="end"
                      variant="contained"
                      className={classes.button}
                    >
                      Generate
                    </LoadingButton>
                    <Button
                      secondary
                      endIcon={<GetApp />}
                      disabled={!text || text?.length === 0}
                      onClick={() => {
                        const blob = new Blob([text], { type: "text/plain" });
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = `${title}_${dateobs}.txt`;
                        link.click();
                      }}
                      className={classes.button}
                    >
                      Download
                    </Button>
                  </div>
                </Paper>
              </Grid>
              <Grid item md={8} sm={12}>
                <Paper className={classes.menu}>
                  <Button
                    primary
                    id="gcn-summary-list"
                    onClick={() => setDisplayList(true)}
                  >
                    GCN Summaries List
                  </Button>
                  <Button onClick={handleSaveGcnSummary}>Save</Button>
                  <Button
                    primary
                    id="new-telescope"
                    onClick={() => setDisplayList(false)}
                  >
                    Summary Text
                  </Button>
                </Paper>
                {displayList ? (
                  <Paper elevation={1} className={classes.content}>
                    <div>
                      <GcnSummaryTable
                        summaries={gcnEvent.summaries}
                        setSelectedGcnSummaryId={setSelectedGcnSummaryId}
                        deleteGcnEventSummary={handleDeleteGcnEventSummary}
                      />
                    </div>
                  </Paper>
                ) : (
                  <Paper elevation={1} className={classes.content}>
                    {loading && (
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
                    {!loading && text && (
                      <TextField
                        id="text"
                        label="Text"
                        multiline
                        value={text.replace(/\n/g, "\n")}
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
                    {!loading && !text && (
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
                )}
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

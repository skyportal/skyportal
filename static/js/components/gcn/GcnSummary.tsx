import { useEffect, useState } from "react";
import { makeStyles, withStyles } from "tss-react/mui";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import { grey } from "@mui/material/colors";
import TextField from "@mui/material/TextField";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Checkbox from "@mui/material/Checkbox";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import FormControlLabel from "@mui/material/FormControlLabel";
import LoadingButton from "@mui/lab/LoadingButton";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { showNotification } from "baselayer/components/Notifications";
import {
  SelectLabelWithChips,
  SelectSingleLabelWithChips,
} from "../SelectWithChips";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { fetchGroup } from "../../ducks/group";
import { fetchGroups } from "../../ducks/groups";
import { fetchInstruments } from "../../ducks/instruments";
import { postGcnEventSummary } from "../../ducks/gcnEvent";
import Button from "../Button";
import GcnSummaryTable from "./GcnSummaryTable";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = (makeStyles() as any)((theme: any) => ({
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

const dialogTitleStyles = (theme: any) => ({
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

const DialogTitle = withStyles(
  ({ children, classes, onClose }: any) => (
    <MuiDialogTitle
      {...({ disableTypography: true } as any)}
      className={classes.root}
    >
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
  dialogTitleStyles as any,
);

interface GcnSummaryProps {
  dateobs: string;
}

const GcnSummary = ({ dateobs }: GcnSummaryProps) => {
  const { classes } = useStyles();
  const groups = useAppSelector((state) => state.groups.userAccessible);
  const users = useAppSelector((state) => state["group"]?.users);
  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<any[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);
  const gcnEvent = useAppSelector((state) => state["gcnEvent"]);
  const [nb, setNb] = useState("");
  const [title, setTitle] = useState("Gcn Summary");
  const [subject, setSubject] = useState(`Follow-up on GCN Event ...`);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [localizationName, setLocalizationName] = useState<any>(null);
  const [localizationCumprob, setLocalizationCumprob] = useState("0.95");
  const [numberDetections, setNumberDetections] = useState("2");
  const [numberObservations, setNumberObservations] = useState("1");
  const [showSources, setShowSources] = useState(false);
  const [showGalaxies, setShowGalaxies] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [noText, setNoText] = useState(false);
  const [photometryInWindow, setPhotometryInWindow] = useState(false);
  const [selectedInstruments, setSelectedInstruments] = useState<any[]>([]);
  const [selectedAcknowledgement, setSelectedAcknowledgement] =
    useState<any>(null);

  const gcnSummaryAcknowledgements = useAppSelector(
    (state) => state["config"].gcnSummaryAcknowledgements,
  );

  const acknowledgmentOptions = selectedAcknowledgement
    ? ["Clear selection", ...gcnSummaryAcknowledgements]
    : gcnSummaryAcknowledgements;

  const [loading, setLoading] = useState(false);

  const groups_list = groups.map((group) => ({
    id: group.id,
    label: group.name,
  }));

  const users_list = users?.map((user: any) => ({
    id: user.id,
    label: `${user.first_name} ${user.last_name}`,
  }));

  let sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1: any, i2: any) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  // to each sortedInstrument, add a label field with the instrument name
  sortedInstrumentList = sortedInstrumentList.map((instrument: any) => ({
    ...instrument,
    label: instrument.name,
  }));

  useEffect(() => {
    if (instrumentList?.length === 0) {
      dispatch(fetchInstruments());
    }
  }, []);

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

  const onAcknowledgementSelectChange = (event: any) => {
    if (event.target.value === "Clear selection") {
      setSelectedAcknowledgement(null);
    } else {
      setSelectedAcknowledgement(event.target.value);
    }
  };

  const onUserSelectChange = (event: any) => {
    let new_selected_users: any[] = [];
    event.target.value.forEach((user: any) => {
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

  const onGroupSelectChange = (event: any) => {
    setSelectedGroup(event.target.value);
  };

  const onInstrumentSelectChange = (event: any) => {
    let new_selected_instruments: any[] = [];
    event.target.value.forEach((instrument: any) => {
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
      const params: any = {
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
      dispatch(postGcnEventSummary({ dateobs, params })).then(
        (response: any) => {
          if (response.status === "success") {
            dispatch(
              showNotification("Summary is being generated, please wait"),
            );
          } else {
            dispatch(showNotification("Error generating summary", "error"));
          }
          setLoading(false);
        },
      );
    }
  };

  return (
    <>
      <Button secondary name="gcn_summary" onClick={() => setOpen(true)}>
        Summary
      </Button>
      {open && (
        <Dialog open={open} onClose={handleClose} fullScreen>
          <DialogTitle onClose={handleClose}>Event {dateobs}</DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={3}>
              <Grid size={{ md: 5, sm: 12 }}>
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
                      {gcnEvent.localizations?.map((localization: any) => (
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
                          {...({ label: "Show Sources" } as any)}
                          checked={showSources}
                          onChange={(e) => setShowSources(e.target.checked)}
                        />
                      }
                      label="Show Sources"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          {...({ label: "Show Galaxies" } as any)}
                          checked={showGalaxies}
                          onChange={(e) => setShowGalaxies(e.target.checked)}
                        />
                      }
                      label="Show Galaxies"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          {...({ label: "Show Observations" } as any)}
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
                          checked={noText}
                          onChange={(e) => setNoText(e.target.checked)}
                        />
                      }
                      label="Table(s) Only"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
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
                      {acknowledgmentOptions?.map((acknowledgment: any) => (
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
                  </div>
                </Paper>
              </Grid>
              <Grid size={{ md: 7, sm: 12 }}>
                <Paper elevation={1} className={classes.content}>
                  <div>
                    <GcnSummaryTable
                      dateobs={dateobs}
                      summaries={gcnEvent.summaries}
                    />
                  </div>
                </Paper>
              </Grid>
            </Grid>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};

export default GcnSummary;

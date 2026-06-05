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
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import {
  SelectLabelWithChips,
  SelectSingleLabelWithChips,
} from "../SelectWithChips";

import { fetchGroup } from "../../ducks/group";
import { useGetGroupsQuery } from "../../ducks/groups";
import { fetchInstruments } from "../../ducks/instruments";
import {
  deleteGcnEventReport,
  fetchGcnEventReport,
  fetchGcnEventReports,
  postGcnEventReport,
} from "../../ducks/gcnEvent";
import Button from "../Button";
import GcnReportTable from "./GcnReportTable";
import GcnReportEdit from "./GcnReportEdit";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  shortcutButtons: {
    margin: "1rem 0",
  },
  form: {
    display: "flex",
    flexDirection: "column" as const,
    padding: theme.spacing(1),
    alignItems: "left" as any,
    justifyContent: "left" as any,
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
    flexDirection: "row" as const,
    width: "100%",
    gap: theme.spacing(2),
  },
  menu: {
    display: "flex",
    direction: "row" as any,
    justifyContent: "space-around",
    alignItems: "center",
    marginBottom: "1rem",
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
  dialogTitleStyles,
) as any;

interface GcnReportProps {
  dateobs: string;
}

const GcnReport = ({ dateobs }: GcnReportProps) => {
  const { classes } = useStyles();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);
  const gcnEvent = useAppSelector((state) => state["gcnEvent"]);
  const [reportName, setReportName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [localizationName, setLocalizationName] = useState<any>(null);
  const [localizationCumprob, setLocalizationCumprob] = useState("0.95");
  const [numberDetections, setNumberDetections] = useState("2");
  const [showSources, setShowSources] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [showSurveyEfficiencies, setShowSurveyEfficiencies] = useState(false);
  const [photometryInWindow, setPhotometryInWindow] = useState(false);
  const [selectedInstruments, setSelectedInstruments] = useState<any[]>([]);
  const [selectedGcnReportId, setSelectedGcnReportId] = useState<any>(null);

  const [loading, setLoading] = useState(false);

  const groups_list = groups.map((group: any) => ({
    id: group?.id,
    label: group?.name,
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
    label: instrument?.name,
  }));

  useEffect(() => {
    if (instrumentList?.length === 0) {
      dispatch(fetchInstruments());
    }
  }, []);

  useEffect(() => {
    const defaultStartDate = dayjs.utc(dateobs).format("YYYY-MM-DD HH:mm:ss");
    const defaultEndDate = dayjs
      .utc(dateobs)
      .add(7, "day")
      .format("YYYY-MM-DD HH:mm:ss");
    setStartDate(defaultStartDate);
    setEndDate(defaultEndDate);
  }, [dateobs]);

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

  useEffect(() => {
    if (
      dateobs !== null &&
      dateobs !== undefined &&
      !gcnEvent?.reports &&
      !loading
    ) {
      setLoading(true);
      dispatch(fetchGcnEventReports(dateobs)).then(() => {
        setLoading(false);
      });
    }
  }, [dateobs, gcnEvent, dispatch]);

  useEffect(() => {
    const fetchReport = (reportID: any) => {
      dispatch(fetchGcnEventReport({ dateobs, reportID })).then(
        (response: any) => {
          if (response.status !== "success") {
            dispatch(showNotification("Error fetching report", "error"));
          }
        },
      );
    };
    if (
      gcnEvent?.reports?.length > 0 &&
      selectedGcnReportId &&
      selectedGcnReportId !== gcnEvent?.report?.id
    ) {
      fetchReport(selectedGcnReportId);
    }
  }, [gcnEvent, selectedGcnReportId]);

  const handleClose = () => {
    setOpen(false);
  };

  const onGroupSelectChange = (event: any) => {
    setSelectedGroup(event.target.value);
  };

  const onInstrumentSelectChange = (event: any) => {
    let new_selected_instruments: any[] = [];
    event.target.value.forEach((instrument: any) => {
      if (
        !new_selected_instruments.some(
          (selected_instrument) => selected_instrument?.id === instrument?.id,
        )
      ) {
        new_selected_instruments.push(instrument);
      } else {
        // remove the user from the list
        new_selected_instruments = new_selected_instruments.filter(
          (selected_instrument) => selected_instrument?.id !== instrument?.id,
        );
      }
    });
    setSelectedInstruments(new_selected_instruments);
  };

  const validateSubmit = () => {
    let valid = true;

    if (!startDate) {
      dispatch(showNotification("Please select a start date", "error"));
      valid = false;
    }
    if (!endDate) {
      dispatch(showNotification("Please select an end date", "error"));
      valid = false;
    }
    if (!showSources && !showObservations && !showSurveyEfficiencies) {
      dispatch(
        showNotification(
          "Please select at least one type to publish: sources, observations, or survey efficiencies",
          "error",
        ),
      );
      valid = false;
    }
    return valid;
  };

  const handleSubmitGcnReport = async () => {
    if (validateSubmit()) {
      setLoading(true);
      const params: any = {
        reportName,
        groupId: selectedGroup?.id,
        startDate,
        endDate,
        localizationName,
        localizationCumprob,
        numberDetections,
        showSources,
        showObservations,
        showSurveyEfficiencies,
        photometryInWindow,
        instrumentIds: (selectedInstruments || []).map(
          (instrument) => instrument?.id,
        ),
      };
      if (params?.instrumentIds?.length === 0) {
        delete params.instrumentIds;
      }
      dispatch(postGcnEventReport({ dateobs, params })).then(
        (response: any) => {
          if (response.status === "success") {
            dispatch(
              showNotification("Report is being generated, please wait"),
            );
          } else {
            dispatch(showNotification("Error generating report", "error"));
          }
          setLoading(false);
        },
      );
    }
  };

  const handleDeleteGcnReport = (reportID: any) => {
    dispatch(deleteGcnEventReport({ dateobs, reportID })).then(
      (response: any) => {
        if (response.status === "success") {
          dispatch(showNotification("Report deleted"));
        } else {
          dispatch(showNotification("Error deleting report", "error"));
        }
      },
    );
  };

  return (
    <>
      <Button secondary name="gcn_report" onClick={() => setOpen(true)}>
        Report
      </Button>
      {open && (
        <Dialog open={open} onClose={handleClose} fullScreen>
          <DialogTitle onClose={handleClose}>Event {dateobs}</DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={3}>
              <Grid size={{ md: 4, sm: 12 }}>
                <Paper elevation={1} className={classes.form}>
                  <TextField
                    id="reportName"
                    label="Report Name"
                    value={reportName}
                    onChange={(e) => setReportName(e.target.value)}
                  />
                  <SelectSingleLabelWithChips
                    label="Group"
                    id="group-select"
                    initValue={selectedGroup}
                    onChange={onGroupSelectChange}
                    options={groups_list}
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
                      name="gcnReportLocalizationSelect"
                    >
                      {gcnEvent.localizations?.map((localization: any) => (
                        <MenuItem
                          value={localization?.localization_name}
                          key={localization?.localization_name}
                        >
                          {`${localization?.localization_name}`}
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
                          checked={showSurveyEfficiencies}
                          onChange={(e) =>
                            setShowSurveyEfficiencies(e.target.checked)
                          }
                        />
                      }
                      label="Show Survey Efficiencies"
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
                  <div className={classes.buttons}>
                    <LoadingButton
                      onClick={() => handleSubmitGcnReport()}
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
              <Grid size={{ md: 8, sm: 12 }}>
                {!selectedGcnReportId && (
                  <Paper elevation={1} className={classes.content}>
                    <div>
                      <GcnReportTable
                        reports={gcnEvent?.reports}
                        setSelectedGcnReportId={setSelectedGcnReportId}
                        deleteGcnReport={handleDeleteGcnReport}
                      />
                    </div>
                  </Paper>
                )}
                <Dialog
                  open={selectedGcnReportId !== null}
                  onClose={() => setSelectedGcnReportId(null)}
                  fullScreen
                >
                  <DialogTitle onClose={() => setSelectedGcnReportId(null)}>
                    Report {dateobs}:{" "}
                    {gcnEvent?.report?.id && (
                      <a
                        href={`/public/reports/gcn/${gcnEvent?.report?.id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {gcnEvent?.report?.report_name}
                      </a>
                    )}
                  </DialogTitle>
                  <DialogContent dividers>
                    {gcnEvent?.report?.data && (
                      <GcnReportEdit
                        {...({ report: gcnEvent?.report } as any)}
                      />
                    )}
                  </DialogContent>
                </Dialog>
              </Grid>
            </Grid>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};

export default GcnReport;

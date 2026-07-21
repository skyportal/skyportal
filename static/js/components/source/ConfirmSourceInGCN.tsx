import { useGetProfileQuery } from "../../ducks/profile";
import { useState, type ReactNode } from "react";
import Paper from "@mui/material/Paper";
import { makeStyles, withStyles } from "tss-react/mui";
import { Controller, useForm } from "react-hook-form";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import EditIcon from "@mui/icons-material/Edit";
import Close from "@mui/icons-material/Close";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { grey } from "@mui/material/colors";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";

import Button from "../Button";

import {
  useGetSourcesInGcnQuery,
  useSubmitSourceInGcnMutation,
  usePatchSourceInGcnMutation,
  useDeleteSourceInGcnMutation,
} from "../../ducks/sourcesingcn";

dayjs.extend(utc);

const filter: any = createFilterOptions<any>();

const defaultExplanationsHighlight = [
  "LOCAL",
  "NEW - FP",
  "RED - FP",
  "FAST - FP",
  "RED - ALERT",
  "FAST - ALERT",
];

const defaultExplanationsReject = [
  "FAR",
  "OLD - FP",
  "SLOW",
  "ROCK",
  "STELLAR",
  "AGN",
  "BOGUS",
  "SpecReject",
];

const defaultExplanations = defaultExplanationsHighlight.concat(
  defaultExplanationsReject,
);

const useStyles = makeStyles()((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  buttons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  button: {
    maxWidth: "1.2rem",
  },
  buttonIcon: {
    maxWidth: "1.2rem",
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
    <MuiDialogTitle className={classes.root}>
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
);

interface ConfirmSourceInGCNProps {
  dateobs: string;
  localization_name: string;
  localization_cumprob: number;
  source_id: string;
  start_date: string;
  end_date: string;
  sources_id_list: string[];
  // Optional custom trigger: a compact button and/or a different icon, so
  // callers (e.g. the crossmatch list) can match surrounding controls.
  compact?: boolean;
  triggerIcon?: ReactNode;
}

const ConfirmSourceInGCN = ({
  dateobs,
  localization_name,
  localization_cumprob,
  source_id,
  start_date,
  end_date,
  sources_id_list,
  compact = false,
  triggerIcon,
}: ConfirmSourceInGCNProps) => {
  const { classes } = useStyles() as any;
  const { permissions } = useGetProfileQuery().data ?? {};
  const [open, setOpen] = useState(false);

  const { control, getValues, register, reset } = useForm();

  const { data: sourcesingcn = [] } = useGetSourcesInGcnQuery({
    dateobs,
    localizationName: localization_name,
    sourcesIdList: sources_id_list,
  });
  const [submitSourceInGcn] = useSubmitSourceInGcnMutation();
  const [patchSourceInGcn] = usePatchSourceInGcnMutation();
  const [deleteSourceInGcn] = useDeleteSourceInGcnMutation();

  const handleClose = () => {
    setOpen(false);
  };

  const getOptionTextColor = (option: any) => {
    let color = "black";
    if (defaultExplanationsHighlight.includes(option)) {
      color = "green";
    } else if (defaultExplanationsReject.includes(option)) {
      color = "red";
    }
    return color;
  };

  let currentState = "not_vetted";
  let currentExplanation = "";
  let currentNotes = "";
  if (
    sourcesingcn?.length > 0 &&
    sourcesingcn.filter((s: any) => s.obj_id === source_id).length !== 0
  ) {
    if (
      sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]?.confirmed ===
      true
    ) {
      currentState = "confirmed";
      currentExplanation =
        sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]
          ?.explanation || "";
      currentNotes =
        sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]?.notes || "";
    } else if (
      sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]?.confirmed ===
      false
    ) {
      currentState = "rejected";
      currentExplanation =
        sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]
          ?.explanation || "";
      currentNotes =
        sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]?.notes || "";
    } else {
      currentState = "ambiguous";
      currentExplanation =
        sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]
          ?.explanation || "";
      currentNotes =
        sourcesingcn.filter((s: any) => s.obj_id === source_id)[0]?.notes || "";
    }
  }

  const handleVet = async (confirmed: boolean | null) => {
    const data = getValues();
    try {
      if (currentState === "not_vetted") {
        await submitSourceInGcn({
          dateobs,
          data: {
            source_id,
            start_date,
            end_date,
            localization_name,
            localization_cumprob,
            confirmed,
            explanation: data["explanation"],
            notes: data["notes"],
          },
        }).unwrap();
      } else {
        await patchSourceInGcn({
          dateobs,
          source_id,
          data: {
            confirmed,
            explanation: data["explanation"],
            notes: data["notes"],
          },
        }).unwrap();
      }
      reset();
      handleClose();
    } catch {
      // notification handled by baseQuery
    }
  };

  const handleHighlight = () => handleVet(true);

  const handleReject = () => handleVet(false);

  const handleAmbiguous = () => handleVet(null);

  const handleNotVetted = async () => {
    try {
      await deleteSourceInGcn({ dateobs, source_id }).unwrap();
      reset();
      handleClose();
    } catch {
      // notification handled by baseQuery
    }
  };

  return permissions?.includes("Manage GCNs") ? (
    <div>
      <IconButton
        aria-label="open"
        className={classes.closeButton}
        size={compact ? "small" : undefined}
        sx={compact ? { p: 0 } : undefined}
        onClick={() => setOpen(true)}
      >
        {triggerIcon ?? <EditIcon />}
      </IconButton>
      {open && (
        <Paper className={classes.container}>
          <Dialog open={open} onClose={handleClose} maxWidth="md">
            <DialogTitle onClose={handleClose}>
              Highlight/Reject Source {source_id} in GCN {dateobs}
            </DialogTitle>
            <DialogContent dividers>
              <div className={classes.dialogContent}>
                <div>
                  <form onSubmit={(e) => e.preventDefault()}>
                    <Typography variant="subtitle2" className={classes.title}>
                      Classification Explanation
                    </Typography>
                    <Controller
                      render={({ field: { onChange, value } }) => (
                        <Autocomplete
                          id="explanation"
                          freeSolo
                          disableClearable
                          filterOptions={(options, params) => {
                            const filtered = filter(options, params);

                            if (params.inputValue !== "") {
                              filtered.push(params.inputValue);
                            }

                            return filtered;
                          }}
                          // eslint-disable-next-line no-shadow
                          onChange={(_e, value) => onChange(value)}
                          options={defaultExplanations}
                          value={value}
                          renderOption={(props, option) => (
                            <Typography
                              style={{ color: getOptionTextColor(option) }}
                              {...props}
                            >
                              {option}
                            </Typography>
                          )}
                          renderInput={(params) => (
                            <TextField
                              {...params}
                              label="Explanation"
                              variant="outlined"
                              fullWidth
                              onChange={(e) => onChange(e.target.value)}
                            />
                          )}
                        />
                      )}
                      name="explanation"
                      control={control}
                      defaultValue={currentExplanation}
                    />
                    <Typography variant="subtitle2" className={classes.title}>
                      GCN Notes
                    </Typography>
                    <div>
                      <Controller
                        render={({ field: { onChange, value } }) => (
                          <TextField
                            label="Notes"
                            name="notes"
                            inputRef={register("notes") as any}
                            onChange={onChange}
                            value={value}
                            defaultValue={currentNotes}
                          />
                        )}
                        name="notes"
                        control={control}
                      />
                    </div>
                    <div>
                      <Button onClick={handleHighlight}>HIGHLIGHT</Button>
                      <Button onClick={handleReject}>REJECT</Button>
                      <Button onClick={handleAmbiguous}>AMBIGUOUS</Button>
                      <Button onClick={handleNotVetted}>NOT VETTED</Button>
                    </div>
                  </form>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </Paper>
      )}
    </div>
  ) : null;
};

export default ConfirmSourceInGCN;

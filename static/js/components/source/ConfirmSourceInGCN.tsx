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
import { createFilterOptions } from "@mui/material/Autocomplete";
import SearchableSelect from "../SearchableSelect";

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
  source_id: string;
  sources_id_list: string[];
  // Only needed to create an association from scratch (the POST path). Callers
  // acting on one the crossmatch already proposed are patching an existing row
  // and can omit them.
  localization_name?: string;
  localization_cumprob?: number;
  start_date?: string;
  end_date?: string;
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
  const [open, setOpen] = useState(false);

  const { control, getValues, register, reset } = useForm();

  const { data: sourcesingcn = [] } = useGetSourcesInGcnQuery({
    dateobs,
    sourcesIDList: sources_id_list,
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

  // What is already recorded for this source, if anything.
  const saved = sourcesingcn?.find((s: any) => s.obj_id === source_id);
  const savedStatus: string | null = saved?.status ?? null;
  const currentExplanation = saved?.explanation || "";
  const currentNotes = saved?.notes || "";
  const currentState = savedStatus ?? "not_vetted";

  // The verdict buttons select; SAVE commits. Committing on click meant a
  // mis-click was written immediately, and left no chance to type the
  // explanation that records *why* -- which is the whole point of the field.
  const [selected, setSelected] = useState<string | null>(null);
  const openDialog = () => {
    // Start on the verdict already recorded, so the dialog shows where this
    // association stands and SAVE stays inert until something changes.
    setSelected(currentState);
    setOpen(true);
  };

  const handleVet = async (status: string) => {
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
            status,
            explanation: data["explanation"],
            notes: data["notes"],
          },
        }).unwrap();
      } else {
        await patchSourceInGcn({
          dateobs,
          source_id,
          data: {
            status,
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

  const handleSave = () => {
    if (!selected || selected === currentState) {
      return;
    }
    // "Not vetted" is the absence of a verdict, so committing it removes the
    // row rather than storing a status.
    if (selected === "not_vetted") {
      handleNotVetted();
    } else {
      handleVet(selected);
    }
  };

  const handleNotVetted = async () => {
    try {
      await deleteSourceInGcn({ dateobs, source_id }).unwrap();
      reset();
      handleClose();
    } catch {
      // notification handled by baseQuery
    }
  };

  return (
    <div>
      <IconButton
        aria-label="vet gcn crossmatch"
        className={classes.closeButton}
        size={compact ? "small" : undefined}
        sx={compact ? { p: 0 } : undefined}
        onClick={openDialog}
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
                        <SearchableSelect
                          id="explanation"
                          label="Explanation"
                          freeSolo
                          disableClearable
                          filterOptions={(options, params) => {
                            const filtered = filter(options, params);

                            if (params.inputValue !== "") {
                              filtered.push(params.inputValue);
                            }

                            return filtered;
                          }}
                          onChange={(_e, newValue) => onChange(newValue)}
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
                          textFieldProps={{
                            onChange: (e: any) => onChange(e.target.value),
                          }}
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
                      {[
                        ["confirmed", "HIGHLIGHT"],
                        ["rejected", "REJECT"],
                        ["ambiguous", "AMBIGUOUS"],
                        ["not_vetted", "NOT VETTED"],
                      ].map(([status, label]) => (
                        <Button
                          key={status}
                          onClick={() => setSelected(status as string)}
                          primary={selected === status}
                        >
                          {label}
                        </Button>
                      ))}
                      <Button
                        onClick={handleSave}
                        disabled={!selected || selected === currentState}
                        secondary
                      >
                        SAVE
                      </Button>
                    </div>
                  </form>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </Paper>
      )}
    </div>
  );
};

export default ConfirmSourceInGCN;

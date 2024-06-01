import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import { makeStyles, withStyles } from "@mui/styles";
import { Controller, useForm } from "react-hook-form";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import EditIcon from "@mui/icons-material/Edit";
import Close from "@mui/icons-material/Close";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import grey from "@mui/material/colors/grey";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";

import Button from "../Button";

import * as PhotometryValidationAction from "../../ducks/photometry_validation";

const filter = createFilterOptions();

const defaultExplanationsHighlight = ["GOOD SUBTRACTION"];

const defaultExplanationsReject = ["BAD SUBTRACTION", "COSMIC RAY"];

const defaultExplanations = defaultExplanationsHighlight.concat(
  defaultExplanationsReject,
);

const useStyles = makeStyles((theme) => ({
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
);

const PhotometryValidation = ({ phot }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const { permissions } = useSelector((state) => state.profile);
  const [open, setOpen] = useState(false);

  const { control, getValues, register } = useForm();

  const handleClose = () => {
    setOpen(false);
  };

  const getOptionTextColor = (option) => {
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
  if (phot?.validations.length > 0) {
    if (phot?.validations[0]?.validated === true) {
      currentState = "validated";
      currentExplanation = phot?.validations[0]?.explanation || "";
      currentNotes = phot?.validations[0]?.notes || "";
    } else if (phot?.validations[0]?.validated === false) {
      currentState = "rejected";
      currentExplanation = phot?.validations[0]?.explanation || "";
      currentNotes = phot?.validations[0]?.notes || "";
    } else {
      currentState = "ambiguous";
      currentExplanation = phot?.validations[0]?.explanation || "";
      currentNotes = phot?.validations[0]?.notes || "";
    }
  }

  const handleValidate = () => {
    const data = getValues();
    if (currentState === "not_vetted") {
      dispatch(
        PhotometryValidationAction.submitValidation(phot.id, {
          validated: true,
          explanation: data.explanation,
          notes: data.notes,
        }),
      ).then((response) => {
        if (response.status === "success") {
          handleClose();
        }
      });
    } else {
      dispatch(
        PhotometryValidationAction.patchValidation(phot.id, {
          validated: true,
          explanation: data.explanation,
          notes: data.notes,
        }),
      ).then((response) => {
        if (response.status === "success") {
          handleClose();
        }
      });
    }
  };

  const handleReject = () => {
    const data = getValues();
    if (currentState === "not_vetted") {
      dispatch(
        PhotometryValidationAction.submitValidation(phot.id, {
          validated: false,
          explanation: data.explanation,
          notes: data.notes,
        }),
      ).then((response) => {
        if (response.status === "success") {
          handleClose();
        }
      });
    } else {
      dispatch(
        PhotometryValidationAction.patchValidation(phot.id, {
          validated: false,
          explanation: data.explanation,
          notes: data.notes,
        }),
      ).then((response) => {
        if (response.status === "success") {
          handleClose();
        }
      });
    }
  };

  const handleAmbiguous = () => {
    const data = getValues();
    if (currentState === "not_vetted") {
      dispatch(
        PhotometryValidationAction.submitValidation(phot.id, {
          validated: null,
          explanation: data.explanation,
          notes: data.notes,
        }),
      ).then((response) => {
        if (response.status === "success") {
          handleClose();
        }
      });
    } else {
      dispatch(
        PhotometryValidationAction.patchValidation(phot.id, {
          validated: null,
          explanation: data.explanation,
          notes: data.notes,
        }),
      ).then((response) => {
        if (response.status === "success") {
          handleClose();
        }
      });
    }
  };

  const handleNotVetted = () => {
    dispatch(PhotometryValidationAction.deleteValidation(phot.id)).then(
      (response) => {
        if (response.status === "success") {
          handleClose();
        }
      },
    );
  };

  return permissions.includes("Manage sources") ? (
    <div>
      <IconButton
        aria-label="open"
        className={classes.closeButton}
        onClick={() => setOpen(true)}
      >
        <EditIcon />
      </IconButton>
      {open && (
        <Paper className={classes.container}>
          <Dialog
            open={open}
            onClose={handleClose}
            style={{ position: "fixed" }}
            maxWidth="md"
          >
            <DialogTitle onClose={handleClose}>
              Validate/Reject Photometry with {phot.id}
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
                          onChange={(e, value) => onChange(value)}
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
                      Notes
                    </Typography>
                    <div>
                      <Controller
                        render={({ field: { onChange, value } }) => (
                          <TextField
                            label="Notes"
                            name="notes"
                            inputRef={register("notes")}
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
                      <Button onClick={handleValidate}>VALIDATE</Button>
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

PhotometryValidation.propTypes = {
  phot: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    obj_id: PropTypes.string,
    mjd: PropTypes.number,
    mag: PropTypes.number,
    magerr: PropTypes.number,
    limiting_mag: PropTypes.number,
    filter: PropTypes.string,
    magsys: PropTypes.string,
    ra: PropTypes.number,
    dec: PropTypes.number,
    ra_unc: PropTypes.number,
    dec_unc: PropTypes.number,
    assignment_id: PropTypes.number,
    instrument_id: PropTypes.number,
    validations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        notes: PropTypes.string,
        explanation: PropTypes.string,
        validated: PropTypes.bool,
      }),
    ),
  }).isRequired,
};

export default PhotometryValidation;

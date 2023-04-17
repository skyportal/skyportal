import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import EditIcon from "@mui/icons-material/Edit";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import * as shiftActions from "../ducks/shift";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  editIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

const UpdateShift = ({ shift }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [state, setState] = useState({
    name: shift.name,
    description: shift.description,
    required_users_number: shift.required_users_number,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      !shift.name || !shift.description || !shift.required_users_number
    );
    setState({
      name: shift.name,
      description: shift.description,
      required_users_number: shift.required_users_number,
    });
  }, [shift, setInvalid]);

  const handleChange = (e) => {
    const newState = {};
    newState[e.target.name] = e.target.value;
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState) => {
    setIsSubmitting(true);
    const newState = {};
    newState.name = subState.name;
    newState.description = subState.description;
    newState.required_users_number = subState.required_users_number;
    const result = await dispatch(
      shiftActions.updateShift(shift.id, {
        ...newState,
      })
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Shift successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <EditIcon
        data-testid="updateShiftIconButton"
        fontSize="small"
        className={classes.editIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Update Shift Info</DialogTitle>
        <DialogContent>
          <div>
            <TextField
              data-testid="updateShiftNameTextfield"
              size="small"
              label="name"
              value={state.name}
              name="name"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updateShiftDescriptionTextfield"
              size="small"
              label="description"
              value={state.description}
              name="description"
              onChange={handleChange}
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updateShiftRequiredTextfield"
              size="small"
              label="required_users_number"
              value={state.required_users_number}
              name="required_users_number"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <div className={classes.saveButton}>
            <Button
              secondary
              onClick={() => {
                handleSubmit(state);
              }}
              endIcon={<SaveIcon />}
              size="large"
              data-testid="updateShiftSubmitButton"
              disabled={isSubmitting || invalid}
            >
              Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateShift.propTypes = {
  shift: PropTypes.shape({
    id: PropTypes.string,
    name: PropTypes.string,
    required_users_number: PropTypes.number,
    description: PropTypes.string,
  }).isRequired,
};

export default UpdateShift;

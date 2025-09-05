import React, { useEffect, useState } from "react";
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
import Button from "../Button";
import * as shiftsActions from "../../ducks/shifts";

const useStyles = makeStyles(() => ({
  editIcon: {
    margin: "0 1rem",
    cursor: "pointer",
    color: "gray",
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

  useEffect(() => {
    setState({
      name: shift.name,
      description: shift.description,
      required_users_number: shift.required_users_number,
    });
  }, [shift]);

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
    if (!subState.name) {
      dispatch(showNotification("Please enter a name for the shift.", "error"));
      setIsSubmitting(false);
      return;
    }
    newState.name = subState.name;
    newState.description = subState.description || "";
    if (subState.required_users_number === "") {
      newState.required_users_number = null;
    } // next we verify that its a number
    else if (
      Number.isNaN(subState.required_users_number) ||
      subState.required_users_number < 0
    ) {
      dispatch(
        showNotification(
          "Please enter a positive number for required users.",
          "error",
        ),
      );
      setIsSubmitting(false);
      return;
    } else if (
      parseInt(subState.required_users_number, 10) <
        shift.required_users_number &&
      shift?.shift_users?.length > subState.required_users_number
    ) {
      dispatch(
        showNotification(
          "Cannot reduce required users number below current number of users signed up for shift. Please remove users first or don't specify a required user number",
          "error",
        ),
      );
      setIsSubmitting(false);
      return;
    } else {
      newState.required_users_number = subState.required_users_number;
    }
    const result = await dispatch(
      shiftsActions.updateShift(shift.id, {
        ...newState,
      }),
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Update Shift Info</DialogTitle>
        <DialogContent>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
          >
            <TextField
              data-testid="updateShiftNameTextfield"
              size="small"
              label="name"
              value={state.name || ""}
              name="name"
              onChange={handleChange}
              variant="outlined"
              sx={{ mt: 1 }}
            />
            <TextField
              data-testid="updateShiftDescriptionTextfield"
              size="small"
              label="description"
              value={state.description || ""}
              name="description"
              onChange={handleChange}
              variant="outlined"
            />
            <TextField
              data-testid="updateShiftRequiredTextfield"
              size="small"
              label="required_users_number"
              value={state.required_users_number || ""}
              name="required_users_number"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
            <div style={{ textAlign: "center" }}>
              <Button
                secondary
                onClick={() => {
                  handleSubmit(state);
                }}
                endIcon={<SaveIcon />}
                size="large"
                data-testid="updateShiftSubmitButton"
                disabled={isSubmitting}
              >
                Save
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

UpdateShift.propTypes = {
  shift: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    required_users_number: PropTypes.number,
    description: PropTypes.string,
    shift_users: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
      }),
    ),
  }).isRequired,
};

export default UpdateShift;

import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import FormValidationError from "./FormValidationError";
import * as photActions from "../ducks/photometry";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
}));

const UpdatePhotometry = ({ phot }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [state, setState] = useState({
    mjd: phot.mjd,
    mag: phot.mag,
    magerr: phot.magerr,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      !phot.mjd || isNaN(phot.mjd)
    );
    setState({
      mjd: phot.mjd,
      mag: phot.mag,
      magerr: phot.magerr,
      limiting_mag: phot.limiting_mag,
    });
  }, [phot, setInvalid]);

  const handleChange = (e) => {
    const newState = {};
    newState[e.target.name] = parseFloat(e.target.value);
    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState) => {
    setIsSubmitting(true);
    const newState = {};

    // editable quantities
    newState.mjd = subState.mjd;
    newState.mag = subState.mag;
    newState.magerr = subState.magerr;
    newState.limiting_mag = subState.limiting_mag;

    // preserved quantities
    newState.obj_id = phot.obj_id;
    newState.ra = phot.ra;
    newState.dec = phot.dec;
    newState.ra_unc = phot.ra_unc;
    newState.dec_unc = phot.dec_unc;
    newState.filter = phot.filter;
    newState.magsys = phot.magsys;
    newState.assignment_id = phot.assignment_id;
    newState.instrument_id = phot.instrument_id;

    const result = await dispatch(
      photActions.updatePhotometry(phot.id, {
        ...newState,
      })
    );
    setIsSubmitting(false);
    if (result.status === "success") {
      dispatch(showNotification("Photometry successfully updated."));
      setDialogOpen(false);
    }
  };

  return (
    <>
      <Button
        primary
        data-testid="updatePhotometryIconButton"
        size="small"
        type="submit"
        onClick={() => {
          setDialogOpen(true);
        }}
      >
        Edit
      </Button>
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Update Photometry</DialogTitle>
        <DialogContent>
          <div>
            {invalid && (
              <FormValidationError message="Please enter a valid float" />
            )}
            <TextField
              data-testid="updatePhotometryMJDTextfield"
              size="small"
              label="mjd"
              value={state.mjd}
              name="mjd"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updatePhotometryMagTextfield"
              size="small"
              label="mag"
              value={state.mag}
              name="mag"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updatePhotometryMagerrTextfield"
              size="small"
              label="magerr"
              value={state.magerr}
              name="magerr"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <p />
          <div>
            <TextField
              data-testid="updatePhotometryLimitingMagTextfield"
              size="small"
              label="limiting_mag"
              value={state.limiting_mag}
              name="limiting_mag"
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
              data-testid="updatePhotometrySubmitButton"
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

UpdatePhotometry.propTypes = {
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
  }).isRequired,
};

export default UpdatePhotometry;

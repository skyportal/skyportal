import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import * as photActions from "../../ducks/photometry";

const useStyles = makeStyles(() => ({
  Select: {
    width: "100%",
  },
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
}));

const UpdatePhotometry = ({ phot, magsys }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { instrumentList } = useSelector((state) => state.instruments);

  const [state, setState] = useState({
    mjd: phot.mjd,
    mag: phot.mag,
    magerr: phot.magerr,
    limiting_mag: phot.limiting_mag,
    filter: phot.filter,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  const instrument = instrumentList.find((x) => x.id === phot.instrument_id);

  useEffect(() => {
    setInvalid(
      // eslint-disable-next-line no-restricted-globals
      !phot.mjd || isNaN(phot.mjd),
    );
    setState({
      mjd: phot.mjd,
      mag: phot.mag,
      magerr: phot.magerr,
      limiting_mag: phot.limiting_mag,
      filter: phot.filter,
    });
  }, [phot, setInvalid]);

  const handleChange = (e) => {
    const newState = {};
    if (Number.isNaN(parseFloat(e.target.value))) {
      newState[e.target.name] = e.target.value;
    } else {
      newState[e.target.name] = parseFloat(e.target.value);
    }

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
    newState.filter = subState.filter;
    newState.magsys = magsys;

    // preserved quantities
    newState.obj_id = phot.obj_id;
    newState.ra = phot.ra;
    newState.dec = phot.dec;
    newState.ra_unc = phot.ra_unc;
    newState.dec_unc = phot.dec_unc;
    newState.assignment_id = phot.assignment_id;
    newState.instrument_id = phot.instrument_id;

    const result = await dispatch(
      photActions.updatePhotometry(phot.id, {
        ...newState,
      }),
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
              label="MJD"
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
              label="Magnitude"
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
              label="Magnitude Error"
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
              label="Limiting Magnitude"
              value={state.limiting_mag}
              name="limiting_mag"
              onChange={handleChange}
              type="number"
              variant="outlined"
            />
          </div>
          <div>
            <InputLabel id="filterSelectLabel">Filter</InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="filterSelectLabel"
              value={state.filter}
              onChange={handleChange}
              name="filter"
              data-testid="filterSelect"
              className={classes.Select}
            >
              {instrument?.filters?.map((filt) => (
                <MenuItem
                  value={filt}
                  key={filt}
                  className={classes.SelectItem}
                >
                  {filt}
                </MenuItem>
              ))}
            </Select>
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
  magsys: PropTypes.string.isRequired,
};

export default UpdatePhotometry;

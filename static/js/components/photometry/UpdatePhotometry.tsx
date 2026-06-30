import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import SaveIcon from "@mui/icons-material/Save";
import TextField from "@mui/material/TextField";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import FormValidationError from "../FormValidationError";
import { useUpdatePhotometryMutation } from "../../ducks/photometry";
import { useGetInstrumentsQuery } from "../../ducks/instruments";

const useStyles = makeStyles()(() => ({
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

interface UpdatePhotometryProps {
  phot: {
    id?: string | number;
    obj_id?: string;
    mjd?: number;
    mag?: number;
    magerr?: number;
    limiting_mag?: number;
    filter?: string;
    magsys?: string;
    ra?: number;
    dec?: number;
    ra_unc?: number;
    dec_unc?: number;
    assignment_id?: number;
    instrument_id?: number;
    [key: string]: any;
  };
  magsys: string;
}

const UpdatePhotometry = ({ phot, magsys }: UpdatePhotometryProps) => {
  const { classes } = useStyles() as any;
  const dispatch = useAppDispatch();
  const [updatePhotometry] = useUpdatePhotometryMutation();

  const { data: instrumentList = [] } = useGetInstrumentsQuery() as {
    data: any[];
  };

  const [state, setState] = useState<any>({
    mjd: phot.mjd,
    mag: phot.mag,
    magerr: phot.magerr,
    limiting_mag: phot.limiting_mag,
    filter: phot.filter,
    instrument_id: phot.instrument_id,
  });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(true);

  const selectedInstrument = instrumentList.find(
    (x: any) => x.id === state.instrument_id,
  );

  useEffect(() => {
    setInvalid(!phot.mjd || isNaN(phot.mjd));
    setState({
      mjd: phot.mjd,
      mag: phot.mag,
      magerr: phot.magerr,
      limiting_mag: phot.limiting_mag,
      filter: phot.filter,
      instrument_id: phot.instrument_id,
    });
  }, [phot, setInvalid]);

  const handleChange = (e: any) => {
    const newState: any = {};

    if (e.target.name === "instrument_id") {
      const newInstrumentId = parseInt(e.target.value, 10);
      newState.instrument_id = newInstrumentId;

      const newInstrument = instrumentList.find(
        (x: any) => x.id === newInstrumentId,
      );
      if (newInstrument?.filters?.length > 0) {
        newState.filter = newInstrument.filters[0];
      } else {
        newState.filter = "";
      }
    } else if (e.target.name === "filter") {
      newState[e.target.name] = e.target.value;
    } else {
      // Accept both "." and "," as the decimal separator so values copy-pasted
      // from the table (which always uses ".") work regardless of locale.
      const normalized =
        typeof e.target.value === "string"
          ? e.target.value.replace(",", ".")
          : e.target.value;
      if (Number.isNaN(parseFloat(normalized))) {
        newState[e.target.name] = e.target.value;
      } else {
        newState[e.target.name] = parseFloat(normalized);
      }
    }

    setState({
      ...state,
      ...newState,
    });
  };

  const handleSubmit = async (subState: any) => {
    setIsSubmitting(true);
    const newState: any = {};

    // editable quantities
    newState.mjd = subState.mjd;
    newState.mag = subState.mag;
    newState.magerr = subState.magerr;
    newState.limiting_mag = subState.limiting_mag;
    newState.filter = subState.filter;
    newState.instrument_id = subState.instrument_id;
    newState.magsys = magsys;

    Object.keys(newState).forEach((key) => {
      if (
        newState[key] === null ||
        newState[key] === undefined ||
        newState[key] === ""
      ) {
        delete newState[key];
      }
    });

    if (
      newState?.limiting_mag === undefined &&
      newState?.mag === undefined &&
      newState?.magerr === undefined
    ) {
      dispatch(
        showNotification(
          "Please specify both mag and magerr, or a limiting_mag",
          "error",
        ),
      );
      setIsSubmitting(false);
      return;
    }

    if (
      (newState?.mag === undefined && newState?.magerr !== undefined) ||
      (newState?.mag !== undefined && newState?.magerr === undefined)
    ) {
      dispatch(showNotification("Please specify both mag and magerr", "error"));
      setIsSubmitting(false);
      return;
    }

    // preserved quantities
    newState.obj_id = phot.obj_id;
    newState.ra = phot.ra;
    newState.dec = phot.dec;
    newState.ra_unc = phot.ra_unc;
    newState.dec_unc = phot.dec_unc;
    newState.assignment_id = phot.assignment_id;

    if (newState?.mag === undefined) {
      newState.mag = null;
    }
    if (newState?.magerr === undefined) {
      newState.magerr = null;
    }
    if (newState?.limiting_mag === undefined) {
      newState.limiting_mag = null;
    }

    if (phot.id == null) {
      setIsSubmitting(false);
      return;
    }
    try {
      await updatePhotometry({
        id: phot.id,
        photometry: { ...newState },
      }).unwrap();
      dispatch(showNotification("Photometry successfully updated."));
      setDialogOpen(false);
    } catch {
      // error notification handled by the baseQuery
    }
    setIsSubmitting(false);
  };

  return (
    <>
      <IconButton
        data-testid="updatePhotometryIconButton"
        size="small"
        type="submit"
        onClick={() => {
          setDialogOpen(true);
        }}
      >
        <EditIcon />
      </IconButton>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
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
              type="text"
              inputProps={{ inputMode: "decimal" }}
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
              type="text"
              inputProps={{ inputMode: "decimal" }}
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
              type="text"
              inputProps={{ inputMode: "decimal" }}
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
              type="text"
              inputProps={{ inputMode: "decimal" }}
              variant="outlined"
            />
          </div>
          <p />
          <div className={classes.formField}>
            <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="instrumentSelectLabel"
              value={state.instrument_id}
              onChange={handleChange}
              name="instrument_id"
              data-testid="instrumentSelect"
              className={classes.Select}
            >
              {instrumentList?.map((instrument: any) => (
                <MenuItem
                  value={instrument.id}
                  key={instrument.id}
                  className={classes.SelectItem}
                >
                  {instrument.name}
                </MenuItem>
              ))}
            </Select>
          </div>
          <div className={classes.formField}>
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
              {selectedInstrument?.filters?.map((filt: any) => (
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

export default UpdatePhotometry;

import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import MUIDataTable from "mui-datatables";
import { makeStyles } from "@material-ui/core/styles";
import Typography from "@material-ui/core/Typography";
import { useForm, Controller } from "react-hook-form";
import Autocomplete from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";

import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "./FormValidationError";

import * as photometryActions from "../ducks/photometry";
import * as spectraActions from "../ducks/spectra";
import * as sourceActions from "../ducks/source";


const createPhotRow = (id, mjd, mag, magerr, limiting_mag, instrument, filter) => (
  {
    id,
    mjd: Number(mjd).toFixed(3),
    mag: mag === null ? null : Number(mag).toFixed(4),
    magerr: magerr === null ? null : Number(magerr).toFixed(4),
    limiting_mag: Number(limiting_mag).toFixed(4),
    instrument,
    filter
  }
);

const createSpecRow = (id, instrument) => (
  {
    id,
    instrument
  }
);

const photHeadCells = [
  { name: "id", label: "ID" },
  { name: "mjd", label: "MJD" },
  { name: "mag", label: "Mag" },
  { name: "magerr", label: "Mag Error" },
  { name: "limiting_mag", label: "Limiting Mag" },
  { name: "instrument", label: "Instrument" },
  { name: "filter", label: "Filter" },
];

const specHeadCells = [
  { name: "id", label: "ID" },
  { name: "instrument", label: "Instrument" },
];

const useStyles = makeStyles(() => ({
  groupSelect: {
    width: "20rem",
  },
}));

const ShareDataForm = ({ route }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [selectedPhotRows, setSelectedPhotRows] = useState([]);
  const [selectedSpecRows, setSelectedSpecRows] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const groups = useSelector((state) => state.groups);
  const photometry = useSelector((state) => state.photometry);
  const spectra = useSelector((state) => state.spectra);
  const allGroups = groups.all;

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    dispatch(photometryActions.fetchSourcePhotometry(route.id));
    dispatch(spectraActions.fetchSourceSpectra(route.id));
  }, [route.id, dispatch]);

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.groups.length >= 1;
  };

  const onSubmit = async (groupsFormData) => {
    const selectedPhotIDs = selectedPhotRows.map((idx) => photometry[route.id][idx].id);
    const selectedSpecIDs = selectedSpecRows.map((idx) => spectra[route.id][idx].id);
    setIsSubmitting(true);
    const data = {
      groupIDs: groupsFormData.groups.map((g) => g.id),
      photometryIDs: selectedPhotIDs,
      spectrumIDs: selectedSpecIDs,
    };
    const result = await dispatch(sourceActions.shareData(data));
    if (result.status === "success") {
      dispatch(showNotification("Data successfully shared"));
      reset({ groups: [] });
      setSelectedPhotRows([]);
      setSelectedSpecRows([]);
    }
    setIsSubmitting(false);
  };

  if (!photometry[route.id] || !allGroups || !spectra[route.id]) {
    return <>Loading...</>;
  }

  const photRows = photometry[route.id].map((phot) => (
    createPhotRow(phot.id, phot.mjd, phot.mag, phot.magerr, phot.limiting_mag,
      phot.instrument_name, phot.filter)));

  const specRows = spectra[route.id].map((spec) => (
    createSpecRow(spec.id, spec.instrument_name)));

  const options = {
    textLabels: {
      body: {
        noMatch: "",
      }
    },
    filter: true,
    selectableRows: "multiple",
    selectableRowsOnClick: true,
    filterType: "dropdown",
    responsive: "vertical",
    rowsPerPage: 10,
    selectableRowsHeader: true,
    customToolbarSelect: () => { },
    download: false,
    print: false
  };

  return (
    <>
      <div>
        <Typography variant="h5">
          Share Source Data
        </Typography>
      </div>
      <br />
      <div>
        <MUIDataTable
          columns={photHeadCells}
          data={photRows}
          title="Photometry"
          options={{
            ...options,
            rowsSelected: selectedPhotRows,
            onRowSelectionChange: (rowsSelectedData, allRows, rowsSelected) => {
              setSelectedPhotRows(rowsSelected);
            }
          }}
        />
        <br />
        <MUIDataTable
          columns={specHeadCells}
          data={specRows}
          title="Spectra"
          options={{
            ...options,
            rowsSelected: selectedSpecRows,
            onRowSelectionChange: (rowsSelectedData, allRows, rowsSelected) => {
              setSelectedSpecRows(rowsSelected);
            }
          }}
        />
      </div>
      <br />
      <div>
        <form onSubmit={handleSubmit(onSubmit)}>
          {
            !!errors.groups &&
              <FormValidationError message="Please select at least one group/user" />
          }
          <Controller
            name="groups"
            as={(
              <Autocomplete
                multiple
                options={allGroups}
                getOptionLabel={(group) => group.name}
                filterSelectedOptions
                renderInput={(params) => (
                  <TextField
                    // eslint-disable-next-line react/jsx-props-no-spreading
                    {...params}
                    error={!!errors.groups}
                    variant="outlined"
                    label="Select Groups/Users"
                    className={classes.groupSelect}
                  />
                )}
              />
              )}
            control={control}
            onChange={([, data]) => data}
            rules={{ validate: validateGroups }}
            defaultValue={[]}
          />
          <br />
          <div>
            <Button
              variant="contained"
              type="submit"
              name="submitShareButton"
              disabled={isSubmitting}
            >
              Submit
            </Button>
          </div>
          <div style={{ display: isSubmitting ? "block" : "none" }}>
            Processing...
          </div>
        </form>
      </div>
    </>
  );
};
ShareDataForm.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired,
};

export default ShareDataForm;

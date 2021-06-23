import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import MUIDataTable from "mui-datatables";
import { makeStyles } from "@material-ui/core/styles";
import Typography from "@material-ui/core/Typography";
import { useForm, Controller } from "react-hook-form";
import Autocomplete from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import IconButton from "@material-ui/core/IconButton";
import DeleteForeverIcon from "@material-ui/icons/DeleteForever";
import GetAppIcon from "@material-ui/icons/GetApp";
import Dialog from "@material-ui/core/Dialog";
import Grid from "@material-ui/core/Grid";
import DialogContent from "@material-ui/core/DialogContent";
import TableRow from "@material-ui/core/TableRow";
import TableCell from "@material-ui/core/TableCell";
import Papa from "papaparse";

import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "./FormValidationError";
import CommentList from "./CommentList";

import * as photometryActions from "../ducks/photometry";
import * as spectraActions from "../ducks/spectra";
import * as sourceActions from "../ducks/source";
import { useSourceStyles } from "./SourceDesktop";
import { deleteSpectrum } from "../ducks/spectra";

function get_filename(spectrum) {
  return `${spectrum.obj_id}_${spectrum.instrument_name}_${spectrum.observed_at}.csv`;
}

function to_csv(spectrum) {
  const formatted = [];
  spectrum.wavelengths.forEach((wave, i) => {
    const obj = {};
    obj.wavelength = wave;
    obj.flux = spectrum.fluxes[i];
    if (spectrum.fluxerr) {
      obj.fluxerr = spectrum.fluxerr[i];
    }
    formatted.push(obj);
  });
  return Papa.unparse(formatted);
}

const UserContactLink = ({ user }) => {
  const display_string =
    user.first_name && user.last_name
      ? `${user.first_name} ${user.last_name}`
      : user.username;
  return (
    <div>
      {user.contact_email && (
        <a href={`mailto:${user.contact_email}`}>{display_string}</a>
      )}
      {!user.contact_email && <p>{display_string}</p>}
    </div>
  );
};

UserContactLink.propTypes = {
  user: PropTypes.shape({
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    username: PropTypes.string.isRequired,
    contact_email: PropTypes.string,
  }).isRequired,
};

const Plot = React.lazy(() => import(/* webpackChunkName: "Bokeh" */ "./Plot"));

const createPhotRow = (
  id,
  mjd,
  mag,
  magerr,
  limiting_mag,
  instrument,
  filter,
  groups
) => ({
  id,
  mjd: Number(mjd).toFixed(3),
  mag: mag === null ? null : Number(mag).toFixed(4),
  magerr: magerr === null ? null : Number(magerr).toFixed(4),
  limiting_mag: Number(limiting_mag).toFixed(4),
  instrument,
  filter,
  groups,
});

const createSpecRow = (
  id,
  instrument,
  observed,
  groups,
  owner,
  reducers,
  observers
) => ({
  id,
  instrument,
  observed,
  groups,
  owner,
  reducers,
  observers,
});

const photHeadCells = [
  { name: "id", label: "ID" },
  { name: "mjd", label: "MJD" },
  { name: "mag", label: "Mag" },
  { name: "magerr", label: "Mag Error" },
  { name: "limiting_mag", label: "Limiting Mag" },
  { name: "instrument", label: "Instrument" },
  { name: "filter", label: "Filter" },
  { name: "groups", label: "Currently visible to" },
];

const useStyles = makeStyles(() => ({
  groupSelect: {
    width: "20rem",
  },
}));

const SpectrumRow = ({ rowData, route }) => {
  const styles = useSourceStyles();
  const colSpan = rowData.length + 1;
  return (
    <TableRow>
      <TableCell colSpan={colSpan}>
        <Grid container direction="row" justify="center" alignItems="center">
          <Grid item className={styles.photometryContainer} sm={6}>
            <Suspense fallback={<div>Loading spectroscopy plot...</div>}>
              <Plot
                className={styles.plot}
                // eslint-disable-next-line react/prop-types
                url={`/api/internal/plot/spectroscopy/${route.id}?spectrumID=${rowData[0]}`}
              />
            </Suspense>
          </Grid>
          <Grid
            item
            data-testid={`individual-spectrum-id_${rowData[0]}`}
            sm={6}
          >
            <Typography variant="h6">Comments</Typography>
            <CommentList
              associatedResourceType="spectrum"
              objID={route.id}
              spectrumID={rowData[0]}
            />
          </Grid>
        </Grid>
      </TableCell>
    </TableRow>
  );
};

SpectrumRow.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string.isRequired,
  }).isRequired,
  rowData: PropTypes.arrayOf(PropTypes.number).isRequired,
};

const ManageDataForm = ({ route }) => {
  const classes = useStyles();

  const dispatch = useDispatch();
  const [selectedPhotRows, setSelectedPhotRows] = useState([]);
  const [selectedSpecRows, setSelectedSpecRows] = useState([]);
  const [openedSpecRows, setOpenedSpecRows] = useState([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const { all: groups } = useSelector((state) => state.groups);
  const photometry = useSelector((state) => state.photometry);
  const spectra = useSelector((state) => state.spectra);

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
    const selectedPhotIDs = selectedPhotRows.map(
      (idx) => photometry[route.id][idx].id
    );
    const selectedSpecIDs = selectedSpecRows.map(
      (idx) => spectra[route.id][idx].id
    );
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

  if ((!photometry[route.id] && !spectra[route.id]) || !groups) {
    return <>Loading...</>;
  }

  const photRows = photometry[route.id]
    ? photometry[route.id].map((phot) =>
        createPhotRow(
          phot.id,
          phot.mjd,
          phot.mag,
          phot.magerr,
          phot.limiting_mag,
          phot.instrument_name,
          phot.filter,
          phot.groups.map((group) => group.name).join(", ")
        )
      )
    : [];

  const sourceSpectra = spectra[route.id];
  const specRows = sourceSpectra
    ? sourceSpectra.map((spec) =>
        createSpecRow(
          spec.id,
          spec.instrument_name,
          spec.observed_at,
          spec.groups.map((group) => group.name).join(", "),
          spec.owner,
          spec.reducers,
          spec.observers
        )
      )
    : [];

  const makeRenderSingleUser = (key) => {
    const RenderSingleUser = (dataIndex) => {
      const user = specRows[dataIndex][key];
      if (user) {
        return <UserContactLink user={user} />;
      }
      return <div />;
    };
    return RenderSingleUser;
  };

  const makeRenderMultipleUsers = (key) => {
    const RenderMultipleUsers = (dataIndex) => {
      const users = specRows[dataIndex][key];
      if (users) {
        return users.map((user) => (
          <UserContactLink user={user} key={user.id} />
        ));
      }
      return <div />;
    };
    return RenderMultipleUsers;
  };

  const DeleteSpectrumButton = (dataIndex) => {
    const specid = specRows[dataIndex].id;
    const [open, setOpen] = useState(false);
    return (
      <div>
        <Dialog
          open={open}
          aria-labelledby="simple-modal-title"
          aria-describedby="simple-modal-description"
          onClose={() => {
            setOpen(false);
          }}
          className={classes.detailedSpecButton}
        >
          <DialogContent>
            <div>
              <Typography variant="h6">
                Are you sure you want to do this?
              </Typography>
              The following operation <em>permanently</em> deletes the spectrum
              from the database. This operation cannot be undone and your data
              cannot be recovered after the fact. You will have to upload the
              spectrum again from scratch.
            </div>
            <div>
              <Button
                onClick={() => {
                  setOpen(false);
                }}
              >
                No, do not delete the spectrum.
              </Button>
              <Button
                onClick={async () => {
                  setOpen(false);
                  const result = await dispatch(deleteSpectrum(specid));
                  if (result.status === "success") {
                    dispatch(showNotification("Spectrum deleted."));
                  }
                }}
                data-testid="yes-delete"
              >
                Yes, delete the spectrum.
              </Button>
            </div>
          </DialogContent>
        </Dialog>
        <IconButton
          onClick={() => {
            setOpen(true);
          }}
          data-testid={`delete-spectrum-button-${specid}`}
        >
          <DeleteForeverIcon />
        </IconButton>
      </div>
    );
  };

  const DownloadSpectrumButton = (dataIndex) => {
    const specid = specRows[dataIndex].id;
    const spectrum = sourceSpectra.find((spec) => spec.id === specid);

    const data = spectrum.original_file_string
      ? spectrum.original_file_string
      : to_csv(spectrum);
    const filename = spectrum.original_file_filename
      ? spectrum.original_file_filename
      : get_filename(spectrum);

    const blob = new Blob([data], { type: "text/plain" });

    return (
      <IconButton href={URL.createObjectURL(blob)} download={filename}>
        <GetAppIcon />
      </IconButton>
    );
  };

  const specHeadCells = [
    { name: "id", label: "ID" },
    { name: "instrument", label: "Instrument" },
    { name: "observed", label: "Observed (UTC)" },
    { name: "groups", label: "Currently visible to" },
    {
      name: "owner",
      label: "Uploaded by",
      options: {
        customBodyRenderLite: makeRenderSingleUser("owner"),
        filter: false,
      },
    },
    {
      name: "reducers",
      label: "Reduced by",
      options: {
        customBodyRenderLite: makeRenderMultipleUsers("reducers"),
        filter: false,
      },
    },
    {
      name: "observers",
      label: "Observed by",
      options: {
        customBodyRenderLite: makeRenderMultipleUsers("observers"),
        filter: false,
      },
    },
    {
      name: "delete",
      label: "Delete",
      options: { customBodyRenderLite: DeleteSpectrumButton, filter: false },
    },
    {
      name: "download",
      label: "Download",
      options: { customBodyRenderLite: DownloadSpectrumButton, filter: false },
    },
  ];

  const options = {
    textLabels: {
      body: {
        noMatch: "",
      },
    },
    filter: true,
    selectableRows: "multiple",
    filterType: "dropdown",
    responsive: "vertical",
    rowsPerPage: 10,
    selectableRowsHeader: true,
    customToolbarSelect: () => {},
    download: false,
    print: false,
  };

  return (
    <>
      <div>
        <Typography variant="h5">
          Share Source Data -&nbsp;
          <Link to={`/source/${route.id}`} role="link">
            {route.id}
          </Link>
        </Typography>
        <p>
          This page allows you to share data for {`${route.id}`} with other
          users or groups. Select the photometry or spectra you would like to
          share from the list below, then select the users or groups you would
          like to share the data with. When you click submit, the access
          permissions on the data will be updated. Data shared via this page
          will not cause the source to be saved to another group.
        </p>
      </div>
      <br />
      <div>
        {!!photometry[route.id] && (
          <MUIDataTable
            columns={photHeadCells}
            data={photRows}
            title="Photometry"
            options={{
              ...options,
              rowsSelected: selectedPhotRows,
              onRowSelectionChange: (
                rowsSelectedData,
                allRows,
                rowsSelected
              ) => {
                setSelectedPhotRows(rowsSelected);
              },
              selectableRowsOnClick: true,
            }}
          />
        )}
        <br />
        {!!spectra[route.id] && (
          <MUIDataTable
            columns={specHeadCells}
            data={specRows}
            title="Spectra"
            options={{
              ...options,
              rowsSelected: selectedSpecRows,
              onRowSelectionChange: (
                rowsSelectedData,
                allRows,
                rowsSelected
              ) => {
                setSelectedSpecRows(rowsSelected);
              },
              expandableRows: true,
              // eslint-disable-next-line react/display-name,no-unused-vars
              renderExpandableRow: (rowData, rowMeta) => (
                <SpectrumRow rowData={rowData} route={route} />
              ),
              expandableRowsOnClick: false,
              rowsExpanded: openedSpecRows,
              onRowExpansionChange: (currentRowsExpanded) => {
                setOpenedSpecRows(currentRowsExpanded.map((i) => i.dataIndex));
              },
            }}
            data-testid="spectrum-table"
          />
        )}
      </div>
      <br />
      <div>
        <form onSubmit={handleSubmit(onSubmit)}>
          {!!errors.groups && (
            <FormValidationError message="Please select at least one group/user" />
          )}
          <Controller
            name="groups"
            render={({ onChange, value, ...props }) => (
              <Autocomplete
                multiple
                id="dataSharingFormGroupsSelect"
                options={groups}
                value={value}
                onChange={(e, data) => onChange(data)}
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
                // eslint-disable-next-line react/jsx-props-no-spreading
                {...props}
              />
            )}
            control={control}
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
ManageDataForm.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default ManageDataForm;

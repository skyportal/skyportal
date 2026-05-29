import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";
import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import GetAppIcon from "@mui/icons-material/GetApp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import Dialog from "@mui/material/Dialog";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import DialogContent from "@mui/material/DialogContent";
import Papa from "papaparse";
import ReactJson from "react-json-view";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { showNotification } from "baselayer/components/Notifications";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarQuickFilter,
} from "@mui/x-data-grid";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import FormValidationError from "../FormValidationError";
import CommentList from "../comment/CommentList";
import AnnotationsTable from "./AnnotationsTable";
import SyntheticPhotometryForm from "../photometry/SyntheticPhotometryForm";

import withRouter from "../withRouter";

import * as photometryActions from "../../ducks/photometry";
import * as spectraActions from "../../ducks/spectra";
import * as sourceActions from "../../ducks/source";
import { deleteSpectrum } from "../../ducks/spectra";
import { useSourceStyles } from "./Source";

import SpectraPlot from "../plot/SpectraPlot";

// Toolbar for the Share-data spectrum grid: exposes a quick-filter search box
// (wrapped with a stable test id) so tests can filter rows by typing a value.
const SpectrumGridToolbar = () => (
  <GridToolbarContainer>
    <GridToolbarColumnsButton />
    <div data-testid="spectrum-quick-filter">
      <GridToolbarQuickFilter />
    </div>
  </GridToolbarContainer>
);

function get_filename(spectrum) {
  return `${spectrum.obj_id}_${spectrum.instrument_name}_${spectrum.observed_at}.csv`;
}

function to_csv(spectrum) {
  const formatted = [];
  spectrum.wavelengths?.forEach((wave, i) => {
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

const createPhotRow = (
  id,
  mjd,
  mag,
  magerr,
  limiting_mag,
  instrument,
  filter,
  groups,
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
  observers,
  pis,
  origin,
  type,
  label,
  external_reducer,
  external_observer,
  external_pi,
) => ({
  id,
  instrument,
  observed,
  groups,
  owner,
  reducers,
  observers,
  pis,
  origin,
  type,
  label,
  external_reducer,
  external_observer,
  external_pi,
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

const useStyles = makeStyles()(() => ({
  groupSelect: {
    width: "20rem",
  },
}));

const SpectrumRow = ({ spectrumID, route, annotations }) => {
  const { classes: styles } = useSourceStyles();
  const spectra = useSelector((state) => state.spectra)[route.id] || [];

  return (
    <div style={{ width: "100%" }}>
      <Grid
        container
        justifyContent="center"
        alignItems="flex-start"
        spacing={2}
      >
        <Grid size={{ sm: 12 }} className={styles.photometryContainer}>
          <Suspense
            fallback={
              <div>
                <CircularProgress color="secondary" />
              </div>
            }
          >
            <SpectraPlot
              spectra={spectra.filter((spec) => spec.id === spectrumID)}
            />
          </Suspense>
        </Grid>
        <Grid
          size={{ sm: 6 }}
          data-testid={`individual-spectrum-id_${spectrumID}`}
        >
          <Paper style={{ padding: "0.5rem" }}>
            <Typography variant="h6">Comments</Typography>
            <Suspense fallback={<CircularProgress />}>
              <CommentList
                associatedResourceType="spectra"
                objID={route.id}
                spectrumID={spectrumID}
              />
            </Suspense>
          </Paper>
        </Grid>
        <Grid size={{ sm: 6 }}>
          <Paper style={{ padding: "0.5rem" }}>
            <Typography variant="h6">Annotations</Typography>
            <AnnotationsTable annotations={annotations} />
          </Paper>
        </Grid>
        <Grid size={{ sm: 6 }}>
          <Paper style={{ padding: "0.5rem" }}>
            <Typography variant="h6">Synthetic Photometry</Typography>
            <SyntheticPhotometryForm spectrum_id={spectrumID} />
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
};

SpectrumRow.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string.isRequired,
  }).isRequired,
  spectrumID: PropTypes.number.isRequired,
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      origin: PropTypes.string.isRequired,
      spectrum_id: PropTypes.number.isRequired,
    }),
  ).isRequired,
};

const ShareDataForm = ({ route }) => {
  const { classes } = useStyles();
  const theme = useTheme();
  const darkTheme = theme.palette.mode === "dark";

  const dispatch = useDispatch();
  const [selectedPhotRows, setSelectedPhotRows] = useState([]);
  const [selectedSpecRows, setSelectedSpecRows] = useState([]);
  const [openedSpecRows, setOpenedSpecRows] = useState([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const { all: groups } = useSelector((state) => state.groups);
  const photometry = useSelector((state) => state.photometry);
  const spectra = useSelector((state) => state.spectra);

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  useEffect(() => {
    dispatch(photometryActions.fetchSourcePhotometry(route.id));
    dispatch(spectraActions.fetchSourceSpectra(route.id));
  }, [route.id, dispatch]);

  const validateGroups = () => {
    const formState = getValues();
    return formState.groups.length >= 1;
  };

  const onSubmit = async (groupsFormData) => {
    setIsSubmitting(true);
    const data = {
      groupIDs: groupsFormData.groups?.map((g) => g.id),
      photometryIDs: selectedPhotRows,
      spectrumIDs: selectedSpecRows,
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
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
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
          phot.groups.map((group) => group.name).join(", "),
        ),
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
          spec.observers,
          spec.pis,
          spec.origin,
          spec.type,
          spec.label,
          spec.external_reducer,
          spec.external_observer,
          spec.external_pi,
        ),
      )
    : [];

  const makeRenderSingleUser = (key) =>
    function RenderSingleUser(params) {
      const user = params.row?.[key];
      return user && <UserContactLink user={user} />;
    };

  const renderMultipleUsers = (users) => {
    return (
      users &&
      users.map((user) => <UserContactLink user={user} key={user.id} />)
    );
  };

  const renderPIs = (params) => {
    const externalPI = params.row?.external_pi;
    const users = params.row?.pis;
    return externalPI || renderMultipleUsers(users);
  };

  const renderReducers = (params) => {
    const externalReducer = params.row?.external_reducer;
    const users = params.row?.reducers;
    return externalReducer || renderMultipleUsers(users);
  };

  const renderReducerContacts = (params) => {
    // Contacts are either the reducers themselves who are
    // SkyPortal users, or users to contact instead of
    // free-text external reducers
    const users = params.row?.reducers;
    return renderMultipleUsers(users);
  };

  const renderObservers = (params) => {
    const externalObserver = params.row?.external_observer;
    const users = params.row?.observers;
    return externalObserver || renderMultipleUsers(users);
  };

  const renderObserverContacts = (params) => {
    // Contacts are either the observers themselves who are
    // SkyPortal users, or users to contact instead of
    // free-text external observers
    const users = params.row?.observers;
    return renderMultipleUsers(users);
  };

  const DeleteSpectrumButton = ({ specid }) => {
    const [open, setOpen] = useState(false);
    return (
      <div>
        <Dialog
          open={open}
          aria-labelledby="simple-modal-title"
          aria-describedby="simple-modal-description"
          onClose={() => setOpen(false)}
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
              <Button onClick={() => setOpen(false)}>Cancel</Button>
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
                Confirm
              </Button>
            </div>
          </DialogContent>
        </Dialog>
        <IconButton
          onClick={() => setOpen(true)}
          size="large"
          color="error"
          data-testid={`delete-spectrum-button-${specid}`}
        >
          <DeleteIcon />
        </IconButton>
      </div>
    );
  };
  DeleteSpectrumButton.propTypes = {
    specid: PropTypes.number.isRequired,
  };

  const DownloadSpectrumButton = ({ specid }) => {
    const spectrum = sourceSpectra.find((spec) => spec.id === specid);
    if (!spectrum) return null;

    const data = spectrum.original_file_string
      ? spectrum.original_file_string
      : to_csv(spectrum);
    const filename = spectrum.original_file_filename
      ? spectrum.original_file_filename
      : get_filename(spectrum);

    const blob = new Blob([data], { type: "text/plain" });

    return (
      <IconButton
        href={URL.createObjectURL(blob)}
        download={filename}
        size="large"
      >
        <GetAppIcon />
      </IconButton>
    );
  };
  DownloadSpectrumButton.propTypes = {
    specid: PropTypes.number.isRequired,
  };

  const AltdataButton = ({ specid }) => {
    const spectrum = sourceSpectra.find((spec) => spec.id === specid);
    const [open, setOpen] = useState(false);
    if (!spectrum?.altdata) return null;
    return (
      <>
        <Dialog
          open={open}
          aria-labelledby="simple-modal-title"
          aria-describedby="simple-modal-description"
          onClose={() => setOpen(false)}
        >
          <DialogContent>
            <div>
              <ReactJson
                src={spectrum.altdata}
                name={false}
                theme={darkTheme ? "monokai" : "rjv-default"}
              />
            </div>
          </DialogContent>
        </Dialog>
        <Button secondary onClick={() => setOpen(true)} size="small">
          Show altdata
        </Button>
      </>
    );
  };
  AltdataButton.propTypes = {
    specid: PropTypes.number.isRequired,
  };

  const toggleSpecExpand = (id) => {
    setOpenedSpecRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const photColumns = [
    { field: "id", headerName: "ID", flex: 1, minWidth: 80 },
    { field: "mjd", headerName: "MJD", flex: 1, minWidth: 100 },
    { field: "mag", headerName: "Mag", flex: 1, minWidth: 90 },
    { field: "magerr", headerName: "Mag Error", flex: 1, minWidth: 100 },
    {
      field: "limiting_mag",
      headerName: "Limiting Mag",
      flex: 1,
      minWidth: 110,
    },
    { field: "instrument", headerName: "Instrument", flex: 1, minWidth: 110 },
    { field: "filter", headerName: "Filter", flex: 1, minWidth: 90 },
    {
      field: "groups",
      headerName: "Currently visible to",
      flex: 1,
      minWidth: 150,
    },
  ];

  const specColumns = [
    {
      field: "__expand",
      headerName: "",
      width: 56,
      sortable: false,
      filterable: false,
      hideable: false,
      disableColumnMenu: true,
      colSpan: (value, row) => (row.__detail ? 100 : 1),
      renderCell: (params) => {
        if (params.row.__detail) {
          const spec = params.row.__source;
          return (
            <SpectrumRow
              spectrumID={spec.id}
              route={route}
              annotations={
                spectra[route.id].find((s) => s.id === spec.id)?.annotations ||
                []
              }
            />
          );
        }
        const expanded = openedSpecRows.includes(params.row.id);
        return (
          <IconButton
            id="expandable-button"
            size="small"
            aria-label="expand row"
            onClick={() => toggleSpecExpand(params.row.id)}
          >
            {expanded ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
          </IconButton>
        );
      },
    },
    { field: "id", headerName: "ID", flex: 1, minWidth: 80 },
    { field: "instrument", headerName: "Instrument", flex: 1, minWidth: 110 },
    { field: "observed", headerName: "Observed (UTC)", flex: 1, minWidth: 150 },
    {
      field: "groups",
      headerName: "Currently visible to",
      flex: 1,
      minWidth: 150,
    },
    {
      field: "owner",
      headerName: "Uploaded by",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: makeRenderSingleUser("owner"),
    },
    {
      field: "pis",
      headerName: "PI(s)",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: renderPIs,
    },
    {
      field: "reducers",
      headerName: "Reduced by",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: renderReducers,
    },
    {
      field: "observers",
      headerName: "Observed by",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: renderObservers,
    },
    {
      field: "reducer_contact",
      headerName: "Reducer contacts",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: renderReducerContacts,
    },
    {
      field: "observer_contact",
      headerName: "Observer contacts",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: renderObserverContacts,
    },
    { field: "origin", headerName: "Origin", flex: 1, minWidth: 100 },
    { field: "type", headerName: "Type", flex: 1, minWidth: 90 },
    { field: "label", headerName: "Label", flex: 1, minWidth: 90 },
    {
      field: "altdata",
      headerName: "Altdata",
      flex: 1,
      minWidth: 110,
      sortable: false,
      filterable: false,
      renderCell: (params) =>
        params.row.__detail ? null : <AltdataButton specid={params.row.id} />,
    },
    {
      field: "delete",
      headerName: "Delete",
      flex: 1,
      minWidth: 90,
      sortable: false,
      filterable: false,
      renderCell: (params) =>
        params.row.__detail ? null : (
          <DeleteSpectrumButton specid={params.row.id} />
        ),
    },
    {
      field: "download",
      headerName: "Download",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: (params) =>
        params.row.__detail ? null : (
          <DownloadSpectrumButton specid={params.row.id} />
        ),
    },
  ];

  // Columns hidden by default (mirrors the previous display:false flags).
  const specColumnVisibilityModel = {
    reducer_contact: false,
    observer_contact: false,
    type: false,
    label: false,
  };

  const specDisplayRows = [];
  specRows.forEach((spec) => {
    specDisplayRows.push(spec);
    if (openedSpecRows.includes(spec.id)) {
      specDisplayRows.push({
        id: `${spec.id}__detail`,
        __detail: true,
        __source: spec,
      });
    }
  });

  return (
    <>
      <div>
        <Link
          to={`/source/${route.id}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            marginBottom: "0.5rem",
          }}
        >
          <ArrowBackIcon fontSize="small" /> Back to source
        </Link>
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
          <div>
            <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
              Photometry
            </Typography>
            <Box sx={{ width: "100%" }}>
              <StyledDataGrid
                autoHeight
                rows={photRows}
                columns={photColumns}
                getRowId={(row) => row.id}
                checkboxSelection
                disableRowSelectionOnClick={false}
                rowSelectionModel={selectedPhotRows}
                onRowSelectionModelChange={(model) =>
                  setSelectedPhotRows(model)
                }
                pageSizeOptions={[10, 25, 50, 100]}
                initialState={{
                  pagination: { paginationModel: { pageSize: 10, page: 0 } },
                }}
                showToolbar
              />
            </Box>
          </div>
        )}

        <br />
        {!!spectra[route.id] && (
          <div data-testid="spectrum-div">
            <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
              Spectra
            </Typography>
            <Box sx={{ width: "100%" }} data-testid="spectrum-table">
              <StyledDataGrid
                autoHeight
                rows={specDisplayRows}
                columns={specColumns}
                getRowId={(row) => row.id}
                getRowHeight={(params) =>
                  params.model.__detail ? "auto" : null
                }
                columnBufferPx={3000}
                checkboxSelection
                disableRowSelectionOnClick={false}
                isRowSelectable={(params) => !params.row.__detail}
                rowSelectionModel={selectedSpecRows}
                onRowSelectionModelChange={(model) =>
                  setSelectedSpecRows(model)
                }
                columnVisibilityModel={specColumnVisibilityModel}
                pageSizeOptions={[10, 25, 50, 100]}
                initialState={{
                  pagination: { paginationModel: { pageSize: 10, page: 0 } },
                }}
                slots={{ toolbar: SpectrumGridToolbar }}
                showToolbar
              />
            </Box>
          </div>
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
            render={({ field: { onChange, value } }) => (
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
            rules={{ validate: validateGroups }}
            defaultValue={[]}
          />
          <br />
          <div>
            <Button
              primary
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
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(ShareDataForm);

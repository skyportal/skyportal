import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import MUIDataTable from "mui-datatables";
import { useTheme } from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import { Controller, useForm } from "react-hook-form";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import GetAppIcon from "@mui/icons-material/GetApp";
import Dialog from "@mui/material/Dialog";
import Grid from "@mui/material/Grid";
import DialogContent from "@mui/material/DialogContent";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import Papa from "papaparse";
import ReactJson from "react-json-view";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import FormValidationError from "./FormValidationError";
import CommentList from "./comment/CommentList";
import AnnotationsTable from "./AnnotationsTable";
import SyntheticPhotometryForm from "./SyntheticPhotometryForm";

import withRouter from "./withRouter";

import * as photometryActions from "../ducks/photometry";
import * as spectraActions from "../ducks/spectra";
import { deleteSpectrum } from "../ducks/spectra";
import * as sourceActions from "../ducks/source";
import { useSourceStyles } from "./source/Source";

import SpectraPlot from "./SpectraPlot";

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

const useStyles = makeStyles(() => ({
  groupSelect: {
    width: "20rem",
  },
}));

const SpectrumRow = ({ rowData, route, annotations }) => {
  const styles = useSourceStyles();
  const colSpan = rowData.length + 1;
  const spectrumID = parseInt(rowData[0], 10);
  const spectra = useSelector((state) => state.spectra)[route.id] || [];

  return (
    <TableRow>
      <TableCell colSpan={colSpan}>
        <Grid
          container
          justifyContent="center"
          alignItems="flex-start"
          spacing={2}
        >
          <Grid item className={styles.photometryContainer} sm={12}>
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
            item
            data-testid={`individual-spectrum-id_${rowData[0]}`}
            sm={6}
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
          <Grid item sm={6}>
            <Paper style={{ padding: "0.5rem" }}>
              <Typography variant="h6">Annotations</Typography>
              <AnnotationsTable annotations={annotations} />
            </Paper>
          </Grid>
          <Grid item sm={6}>
            <Paper style={{ padding: "0.5rem" }}>
              <Typography variant="h6">Synthetic Photometry</Typography>
              <SyntheticPhotometryForm spectrum_id={rowData[0]} />
            </Paper>
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
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      origin: PropTypes.string.isRequired,
      spectrum_id: PropTypes.number.isRequired,
    }),
  ).isRequired,
};

const ShareDataForm = ({ route }) => {
  const classes = useStyles();
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
    const selectedPhotIDs = selectedPhotRows?.map(
      (idx) => photometry[route.id][idx].id,
    );
    const selectedSpecIDs = selectedSpecRows?.map(
      (idx) => spectra[route.id][idx].id,
    );
    setIsSubmitting(true);
    const data = {
      groupIDs: groupsFormData.groups?.map((g) => g.id),
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

  const renderMultipleUsers = (users) => {
    if (users) {
      return users.map((user) => <UserContactLink user={user} key={user.id} />);
    }
    return <div />;
  };

  const renderPIs = (dataIndex) => {
    const externalPI = specRows[dataIndex]?.external_pi;
    const users = specRows[dataIndex]?.pis;
    if (externalPI) {
      return <div>{externalPI}</div>;
    }
    return renderMultipleUsers(users);
  };

  const renderReducers = (dataIndex) => {
    const externalReducer = specRows[dataIndex]?.external_reducer;
    const users = specRows[dataIndex]?.reducers;
    if (externalReducer) {
      return <div>{externalReducer}</div>;
    }
    return renderMultipleUsers(users);
  };

  const renderReducerContacts = (dataIndex) => {
    // Contacts are either the reducers themselves who are
    // SkyPortal users, or users to contact instead of
    // free-text external reducers
    const users = specRows[dataIndex]?.reducers;
    return renderMultipleUsers(users);
  };

  const renderObservers = (dataIndex) => {
    const externalObserver = specRows[dataIndex]?.external_observer;
    const users = specRows[dataIndex]?.observers;
    if (externalObserver) {
      return <div>{externalObserver}</div>;
    }
    return renderMultipleUsers(users);
  };

  const renderObserverContacts = (dataIndex) => {
    // Contacts are either the observers themselves who are
    // SkyPortal users, or users to contact instead of
    // free-text external observers
    const users = specRows[dataIndex]?.observers;
    return renderMultipleUsers(users);
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
          size="large"
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
      <IconButton
        href={URL.createObjectURL(blob)}
        download={filename}
        size="large"
      >
        <GetAppIcon />
      </IconButton>
    );
  };

  const AltdataButton = (dataIndex) => {
    const specid = specRows[dataIndex].id;
    const spectrum = sourceSpectra.find((spec) => spec.id === specid);
    const [open, setOpen] = useState(false);
    return spectrum.altdata ? (
      <>
        <Dialog
          open={open}
          aria-labelledby="simple-modal-title"
          aria-describedby="simple-modal-description"
          onClose={() => {
            setOpen(false);
          }}
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
        <Button
          secondary
          onClick={() => {
            setOpen(true);
          }}
          data-testid={`altdata-spectrum-button-${specid}`}
          size="small"
        >
          Show altdata
        </Button>
      </>
    ) : (
      <div />
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
      name: "pis",
      label: "PI(s)",
      options: {
        customBodyRenderLite: renderPIs,
        filter: false,
      },
    },
    {
      name: "reducers",
      label: "Reduced by",
      options: {
        customBodyRenderLite: renderReducers,
        filter: false,
      },
    },
    {
      name: "observers",
      label: "Observed by",
      options: {
        customBodyRenderLite: renderObservers,
        filter: false,
      },
    },
    {
      name: "reducer_contact",
      label: "Reducer contacts",
      options: {
        customBodyRenderLite: renderReducerContacts,
        filter: false,
        display: false,
      },
    },
    {
      name: "observer_contact",
      label: "Observer contacts",
      options: {
        customBodyRenderLite: renderObserverContacts,
        filter: false,
        display: false,
      },
    },
    {
      name: "origin",
      label: "Origin",
    },
    {
      name: "type",
      label: "Type",
      filter: true,
      display: false,
    },
    {
      name: "label",
      label: "Label",
      filter: false,
      display: false,
    },
    {
      name: "altdata",
      label: "Altdata",
      options: { customBodyRenderLite: AltdataButton, filter: false },
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
      <div data-testid="photometry-div">
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
                  rowsSelected,
                ) => {
                  setSelectedPhotRows(rowsSelected);
                },
                selectableRowsOnClick: true,
              }}
            />
          </div>
        )}

        <br />
        {!!spectra[route.id] && (
          <div data-testid="spectrum-div">
            <MUIDataTable
              columns={specHeadCells}
              data={specRows}
              title="Spectra"
              data-testid="spectrum-table"
              options={{
                ...options,
                rowsSelected: selectedSpecRows,
                onRowSelectionChange: (
                  rowsSelectedData,
                  allRows,
                  rowsSelected,
                ) => {
                  setSelectedSpecRows(rowsSelected);
                },
                expandableRows: true,
                // eslint-disable-next-line react/display-name,no-unused-vars
                renderExpandableRow: (rowData, rowMeta) => (
                  <SpectrumRow
                    rowData={rowData}
                    route={route}
                    annotations={
                      spectra[route.id].find((spec) => spec.id === rowData[0])
                        .annotations
                    }
                  />
                ),
                expandableRowsOnClick: false,
                rowsExpanded: openedSpecRows,
                onRowExpansionChange: (_, expandedRows) => {
                  setOpenedSpecRows(expandedRows.map((i) => i.dataIndex));
                },
              }}
            />
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

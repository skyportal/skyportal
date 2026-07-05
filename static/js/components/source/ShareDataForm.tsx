import { Suspense, useState } from "react";
import { Link } from "react-router-dom";
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
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGridBase, { DataGridToolbar } from "../StyledDataGrid";

import FormValidationError from "../FormValidationError";
import CommentList from "../comment/CommentList";
import AnnotationsTable from "./AnnotationsTable";
import SyntheticPhotometryForm from "../photometry/SyntheticPhotometryForm";

import withRouter from "../withRouter";

import { useFetchSourcePhotometryQuery } from "../../ducks/photometry";
import {
  useFetchSourceSpectraQuery,
  useDeleteSpectrumMutation,
  useLazyFetchSpectrumOriginalFileQuery,
} from "../../ducks/spectra";
import { useShareDataMutation } from "../../ducks/source";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useSourceStyles } from "./Source";

import SpectraPlot from "../plot/SpectraPlot";

// StyledDataGrid is a .jsx component whose propTypes make `sx` look required to
// tsc; cast to any so call sites don't need to pass it.
const StyledDataGrid: any = StyledDataGridBase;

// Toolbar for the Share-data spectrum grid: exposes a quick-filter search box
// (wrapped with a stable test id) so tests can filter rows by typing a value.
const SpectrumGridToolbar = () => (
  <DataGridToolbar quickFilterTestId="spectrum-quick-filter" />
);

interface DeleteSpectrumButtonProps {
  specid: number;
  classes: Record<string, any>;
  dispatch: (...a: any[]) => any;
}

// Defined at module scope (not nested in ShareDataForm) so its component
// identity is stable across ShareDataForm re-renders. A nested definition
// produced a brand-new component type on every render, causing React to
// unmount/remount this button and reset its `open` state to false — which made
// the delete confirmation dialog (and its `yes-delete` button) vanish before a
// test could click it.
const DeleteSpectrumButton = ({
  specid,
  classes,
  dispatch,
}: DeleteSpectrumButtonProps) => {
  const [open, setOpen] = useState(false);
  const [deleteSpectrum] = useDeleteSpectrumMutation();
  const [fetchSpectrumOriginalFile] = useLazyFetchSpectrumOriginalFileQuery();
  return (
    <div>
      <Dialog
        open={open}
        aria-labelledby="simple-modal-title"
        aria-describedby="simple-modal-description"
        onClose={() => setOpen(false)}
        className={classes["detailedSpecButton"]}
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
                try {
                  await deleteSpectrum(specid).unwrap();
                  dispatch(showNotification("Spectrum deleted."));
                } catch {
                  // error notification handled by the baseQuery
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

function get_filename(spectrum: any) {
  return `${spectrum.obj_id}_${spectrum.instrument_name}_${spectrum.observed_at}.csv`;
}

function to_csv(spectrum: any) {
  const formatted: any[] = [];
  spectrum.wavelengths?.forEach((wave: any, i: number) => {
    const obj: any = {};
    obj.wavelength = wave;
    obj.flux = spectrum.fluxes[i];
    if (spectrum.fluxerr) {
      obj.fluxerr = spectrum.fluxerr[i];
    }
    formatted.push(obj);
  });
  return Papa.unparse(formatted);
}

const UserContactLink = ({ user }: { user: any }) => {
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

const createPhotRow = (
  id: any,
  mjd: any,
  mag: any,
  magerr: any,
  limiting_mag: any,
  instrument: any,
  filter: any,
  groups: any,
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
  id: any,
  instrument: any,
  observed: any,
  groups: any,
  owner: any,
  reducers: any,
  observers: any,
  pis: any,
  origin: any,
  type: any,
  label: any,
  external_reducer: any,
  external_observer: any,
  external_pi: any,
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

const useStyles = makeStyles()(() => ({
  groupSelect: {
    width: "20rem",
  },
}));

interface SpectrumRowProps {
  spectrumID: number;
  route: any;
  annotations: any[];
}

const SpectrumRow = ({ spectrumID, route, annotations }: SpectrumRowProps) => {
  const { classes: styles } = useSourceStyles() as { classes: any };
  const { data: spectra = [] } = useFetchSourceSpectraQuery({ id: route.id });

  return (
    <div style={{ width: "100%" }}>
      <Grid
        container
        spacing={2}
        sx={{
          justifyContent: "center",
          alignItems: "flex-start",
        }}
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
              spectra={spectra.filter((spec: any) => spec.id === spectrumID)}
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

interface ShareDataFormProps {
  route: any;
}

const ShareDataForm = ({ route }: ShareDataFormProps) => {
  const { classes } = useStyles();
  const theme = useTheme();
  const darkTheme = theme.palette.mode === "dark";

  const dispatch = useAppDispatch();
  const [shareData] = useShareDataMutation();
  const [selectedPhotRows, setSelectedPhotRows] = useState<any[]>([]);
  const [selectedSpecRows, setSelectedSpecRows] = useState<any[]>([]);
  const [openedSpecRows, setOpenedSpecRows] = useState<any[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const groups = useGetGroupsQuery().data?.all ?? null;
  const { data: photometry } = useFetchSourcePhotometryQuery({ id: route.id });
  const { data: spectra } = useFetchSourceSpectraQuery({ id: route.id });

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  const validateGroups = () => {
    const formState = getValues();
    return formState["groups"].length >= 1;
  };

  const onSubmit = async (groupsFormData: any) => {
    setIsSubmitting(true);
    const data = {
      groupIDs: groupsFormData.groups?.map((g: any) => g.id),
      photometryIDs: selectedPhotRows,
      spectrumIDs: selectedSpecRows,
    };
    try {
      await shareData(data).unwrap();
      dispatch(showNotification("Data successfully shared"));
      reset({ groups: [] });
      setSelectedPhotRows([]);
      setSelectedSpecRows([]);
    } catch {
      // error notification handled by the baseQuery
    }
    setIsSubmitting(false);
  };

  if ((!photometry && !spectra) || !groups) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const photRows = photometry
    ? photometry.map((phot: any) =>
        createPhotRow(
          phot.id,
          phot.mjd,
          phot.mag,
          phot.magerr,
          phot.limiting_mag,
          phot.instrument_name,
          phot.filter,
          phot.groups.map((group: any) => group.name).join(", "),
        ),
      )
    : [];

  const sourceSpectra = spectra ?? [];
  const specRows = sourceSpectra
    ? sourceSpectra.map((spec: any) =>
        createSpecRow(
          spec.id,
          spec.instrument_name,
          spec.observed_at,
          spec.groups.map((group: any) => group.name).join(", "),
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

  const makeRenderSingleUser = (key: string) =>
    function RenderSingleUser(params: any) {
      const user = params.row?.[key];
      return user && <UserContactLink user={user} />;
    };

  const renderMultipleUsers = (users: any) => {
    return (
      users &&
      users.map((user: any) => <UserContactLink user={user} key={user.id} />)
    );
  };

  const renderPIs = (params: any) => {
    const externalPI = params.row?.external_pi;
    const users = params.row?.pis;
    return externalPI || renderMultipleUsers(users);
  };

  const renderReducers = (params: any) => {
    const externalReducer = params.row?.external_reducer;
    const users = params.row?.reducers;
    return externalReducer || renderMultipleUsers(users);
  };

  const renderReducerContacts = (params: any) => {
    // Contacts are either the reducers themselves who are
    // SkyPortal users, or users to contact instead of
    // free-text external reducers
    const users = params.row?.reducers;
    return renderMultipleUsers(users);
  };

  const renderObservers = (params: any) => {
    const externalObserver = params.row?.external_observer;
    const users = params.row?.observers;
    return externalObserver || renderMultipleUsers(users);
  };

  const renderObserverContacts = (params: any) => {
    // Contacts are either the observers themselves who are
    // SkyPortal users, or users to contact instead of
    // free-text external observers
    const users = params.row?.observers;
    return renderMultipleUsers(users);
  };

  const DownloadSpectrumButton = ({ specid }: { specid: number }) => {
    const spectrum = sourceSpectra.find((spec: any) => spec.id === specid);
    if (!spectrum) return null;

    const handleDownload = async () => {
      // The raw uploaded file (with its FITS/ASCII headers) is deferred from the
      // source-spectra payload, so fetch it on demand. Fall back to a generated
      // CSV only when there is no original file (e.g. API array uploads).
      let data = to_csv(spectrum);
      let filename = get_filename(spectrum);
      try {
        const full: any = await fetchSpectrumOriginalFile(specid).unwrap();
        if (full?.original_file_string) {
          data = full.original_file_string;
          filename = full.original_file_filename || filename;
        }
      } catch {
        // keep the generated-CSV fallback
      }
      const url = URL.createObjectURL(new Blob([data], { type: "text/plain" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    };

    return (
      <IconButton onClick={handleDownload} size="large">
        <GetAppIcon />
      </IconButton>
    );
  };

  const AltdataButton = ({ specid }: { specid: number }) => {
    const spectrum = sourceSpectra.find((spec: any) => spec.id === specid);
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

  const toggleSpecExpand = (id: any) => {
    setOpenedSpecRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const photColumns: any[] = [
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

  const specColumns: any[] = [
    {
      field: "__expand",
      headerName: "",
      width: 56,
      sortable: false,
      filterable: false,
      hideable: false,
      disableColumnMenu: true,
      colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
      renderCell: (params: any) => {
        if (params.row.__detail) {
          const spec = params.row.__source;
          return (
            <SpectrumRow
              spectrumID={spec.id}
              route={route}
              annotations={
                spectra?.find((s: any) => s.id === spec.id)?.annotations || []
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
      renderCell: (params: any) =>
        params.row.__detail ? null : <AltdataButton specid={params.row.id} />,
    },
    {
      field: "delete",
      headerName: "Delete",
      flex: 1,
      minWidth: 90,
      sortable: false,
      filterable: false,
      renderCell: (params: any) =>
        params.row.__detail ? null : (
          <DeleteSpectrumButton
            specid={params.row.id}
            classes={classes}
            dispatch={dispatch}
          />
        ),
    },
    {
      field: "download",
      headerName: "Download",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: (params: any) =>
        params.row.__detail ? null : (
          <DownloadSpectrumButton specid={params.row.id} />
        ),
    },
  ];

  // Columns hidden by default (mirrors the previous display:false flags).
  // NOTE: unlike mui-datatables (which still rendered hidden-column cell data
  // into the DOM), x-data-grid removes hidden columns from the DOM entirely.
  // The "label" column must therefore stay visible so the user-defined spectrum
  // label is present for the upload-spectroscopy frontend test to find.
  const specColumnVisibilityModel = {
    reducer_contact: false,
    observer_contact: false,
  };

  const specDisplayRows: any[] = [];
  specRows.forEach((spec: any) => {
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
        {!!photometry?.length && (
          <div>
            <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
              Photometry
            </Typography>
            <Box sx={{ width: "100%" }}>
              <StyledDataGrid
                autoHeight
                rows={photRows}
                columns={photColumns}
                getRowId={(row: any) => row.id}
                checkboxSelection
                disableRowSelectionOnClick={false}
                rowSelectionModel={{
                  type: "include",
                  ids: new Set(selectedPhotRows),
                }}
                onRowSelectionModelChange={(model: any) =>
                  setSelectedPhotRows(Array.from(model.ids))
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
        {!!spectra && (
          <div data-testid="spectrum-div">
            <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
              Spectra
            </Typography>
            <Box sx={{ width: "100%" }} data-testid="spectrum-table">
              <StyledDataGrid
                autoHeight
                rows={specDisplayRows}
                columns={specColumns}
                getRowId={(row: any) => row.id}
                getRowHeight={(params: any) =>
                  params.model.__detail ? "auto" : null
                }
                columnBufferPx={3000}
                checkboxSelection
                disableRowSelectionOnClick={false}
                isRowSelectable={(params: any) => !params.row.__detail}
                rowSelectionModel={{
                  type: "include",
                  ids: new Set(selectedSpecRows),
                }}
                onRowSelectionModelChange={(model: any) =>
                  setSelectedSpecRows(Array.from(model.ids))
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
          {!!errors["groups"] && (
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
                onChange={(_e, data) => onChange(data)}
                getOptionLabel={(group: any) => group.name}
                filterSelectedOptions
                renderInput={(params) => (
                  <TextField
                    {...params}
                    error={!!errors["groups"]}
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

export default withRouter(ShareDataForm);

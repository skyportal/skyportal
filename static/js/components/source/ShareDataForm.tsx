import { useState } from "react";
import { Link } from "react-router-dom";
import { Controller, useForm } from "react-hook-form";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import SearchableSelect from "../SearchableSelect";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import DeleteIcon from "@mui/icons-material/Delete";
import GetAppIcon from "@mui/icons-material/GetApp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Papa from "papaparse";
import ReactJson from "react-json-view";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import Spinner from "../Spinner";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import FormValidationError from "../FormValidationError";
import CommentThread from "../comment/CommentThread";
import AnnotationsTable from "./AnnotationsTable";
import SyntheticPhotometryForm from "../photometry/SyntheticPhotometryForm";
import SpectraPlot from "../plot/SpectraPlot";
import withRouter from "../withRouter";
import { getSpectrumFilename } from "./spectrumFilename";

import { useFetchSourcePhotometryQuery } from "../../ducks/photometry";
import {
  useFetchSourceSpectraQuery,
  useDeleteSpectrumMutation,
  useLazyFetchSpectrumOriginalFileQuery,
} from "../../ducks/spectra";
import { useShareDataMutation } from "../../ducks/source";
import { useGetGroupsQuery } from "../../ducks/groups";

const PhotometryGridToolbar = () => <DataGridToolbar title="Photometry" />;

const SpectrumGridToolbar = () => (
  <DataGridToolbar
    title="Spectra"
    showExport={false}
    quickFilterTestId="spectrum-quick-filter"
  />
);

const spectrumToCsv = (spectrum: any) =>
  Papa.unparse(
    (spectrum.wavelengths ?? []).map((wavelength: number, i: number) => ({
      wavelength,
      flux: spectrum.fluxes[i],
      ...(spectrum.fluxerr ? { fluxerr: spectrum.fluxerr[i] } : {}),
    })),
  );

const UserContactLink = ({ user }: { user: any }) => {
  const name =
    user.first_name && user.last_name
      ? `${user.first_name} ${user.last_name}`
      : user.username;
  return user.contact_email ? (
    <a href={`mailto:${user.contact_email}`}>{name}</a>
  ) : (
    <span>{name}</span>
  );
};

const renderUsers = (users: any[]) =>
  users?.length ? (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
      {users.map((user: any) => (
        <UserContactLink key={user.id} user={user} />
      ))}
    </Box>
  ) : null;

const DeleteSpectrumButton = ({ specid }: { specid: number }) => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const [deleteSpectrum] = useDeleteSpectrumMutation();

  const onDelete = async () => {
    setOpen(false);
    try {
      await deleteSpectrum(specid).unwrap();
      dispatch(showNotification("Spectrum deleted."));
    } catch {
      // error notification handled by the baseQuery
    }
  };

  return (
    <>
      <ConfirmDeletionDialog
        dialogOpen={open}
        closeDialog={() => setOpen(false)}
        deleteFunction={onDelete}
        resourceName="spectrum"
      />
      <IconButton
        onClick={() => setOpen(true)}
        color="error"
        data-testid={`delete-spectrum-button-${specid}`}
      >
        <DeleteIcon />
      </IconButton>
    </>
  );
};

const DownloadSpectrumButton = ({ spectrum }: { spectrum: any }) => {
  const [fetchOriginalFile] = useLazyFetchSpectrumOriginalFileQuery();

  const onDownload = async () => {
    let data = spectrumToCsv(spectrum);
    let filename = getSpectrumFilename(spectrum);
    const original: any = await fetchOriginalFile(spectrum.id)
      .unwrap()
      .catch(() => null);
    if (original?.original_file_string) {
      data = original.original_file_string;
      const uploaded = original.original_file_filename || "";
      filename = getSpectrumFilename(
        spectrum,
        uploaded.includes(".") ? uploaded.split(".").pop() : "ascii",
      );
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
    <IconButton onClick={onDownload}>
      <GetAppIcon />
    </IconButton>
  );
};

const AltdataButton = ({ altdata }: { altdata: any }) => {
  const [open, setOpen] = useState(false);
  const darkTheme = useTheme().palette.mode === "dark";
  if (!altdata) return null;

  return (
    <>
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogContent>
          <ReactJson
            src={altdata}
            name={false}
            theme={darkTheme ? "monokai" : "rjv-default"}
          />
        </DialogContent>
      </Dialog>
      <Button secondary onClick={() => setOpen(true)} size="small">
        Show altdata
      </Button>
    </>
  );
};

const SpectrumDetail = ({
  spectrum,
  objID,
}: {
  spectrum: any;
  objID: string;
}) => (
  <Grid
    container
    spacing={1}
    sx={{ width: "100%", py: 1 }}
    data-testid={`individual-spectrum-id_${spectrum.id}`}
  >
    <Grid size={12}>
      <SpectraPlot spectra={[spectrum]} />
    </Grid>
    <Grid size={{ xs: 12, md: 6 }}>
      <Paper sx={{ p: 1 }}>
        <Typography variant="h6">Comments</Typography>
        <CommentThread
          resourceType="spectra"
          objID={objID}
          spectrumID={spectrum.id}
          maxHeightList="350px"
        />
      </Paper>
    </Grid>
    <Grid size={{ xs: 12, md: 6 }}>
      <Paper sx={{ p: 1 }}>
        <Typography variant="h6">Annotations</Typography>
        <AnnotationsTable annotations={spectrum.annotations || []} />
      </Paper>
    </Grid>
    <Grid size={{ xs: 12, md: 6 }}>
      <Paper sx={{ p: 1 }}>
        <Typography variant="h6">Synthetic Photometry</Typography>
        <SyntheticPhotometryForm spectrum_id={spectrum.id} />
      </Paper>
    </Grid>
  </Grid>
);

const onSelectionChange =
  (rowIds: any[], setSelected: (ids: any[]) => void) => (model: any) =>
    setSelected(
      model.type === "exclude"
        ? rowIds.filter((id) => !model.ids.has(id))
        : Array.from(model.ids),
    );

interface ShareDataFormProps {
  route: any;
}

const ShareDataForm = ({ route }: ShareDataFormProps) => {
  const dispatch = useAppDispatch();
  const [shareData] = useShareDataMutation();
  const [selectedPhotRows, setSelectedPhotRows] = useState<any[]>([]);
  const [selectedSpecRows, setSelectedSpecRows] = useState<any[]>([]);
  const [openedSpecRows, setOpenedSpecRows] = useState<any[]>([]);

  const groups = useGetGroupsQuery().data?.all ?? null;
  const { data: photometry } = useFetchSourcePhotometryQuery({ id: route.id });
  const { data: spectra } = useFetchSourceSpectraQuery({ id: route.id });

  const {
    handleSubmit,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm();

  const onSubmit = async (formData: any) => {
    try {
      await shareData({
        groupIDs: formData.groups?.map((group: any) => group.id),
        photometryIDs: selectedPhotRows,
        spectrumIDs: selectedSpecRows,
      }).unwrap();
      dispatch(showNotification("Data successfully shared"));
      reset({ groups: [] });
      setSelectedPhotRows([]);
      setSelectedSpecRows([]);
    } catch {
      // error notification handled by the baseQuery
    }
  };

  if ((!photometry && !spectra) || !groups) return <Spinner />;

  const groupNames = (item: any) =>
    item.groups.map((group: any) => group.name).join(", ");

  const photRows = (photometry ?? []).map((phot: any) => ({
    id: phot.id,
    mjd: Number(phot.mjd).toFixed(3),
    mag: phot.mag === null ? null : Number(phot.mag).toFixed(4),
    magerr: phot.magerr === null ? null : Number(phot.magerr).toFixed(4),
    limiting_mag: Number(phot.limiting_mag).toFixed(2),
    instrument: phot.instrument_name,
    filter: phot.filter,
    groups: groupNames(phot),
  }));

  const specRows = (spectra ?? []).map((spec: any) => ({
    ...spec,
    instrument: spec.instrument_name,
    observed: spec.observed_at,
    groups: groupNames(spec),
  }));

  const specDisplayRows = specRows.flatMap((row: any) =>
    openedSpecRows.includes(row.id)
      ? [row, { id: `${row.id}__detail`, __detail: true, __source: row }]
      : [row],
  );

  const photColumns = [
    { field: "id", headerName: "ID", flex: 0.5, minWidth: 40 },
    { field: "mjd", headerName: "MJD", flex: 0.5, minWidth: 80 },
    { field: "mag", headerName: "Mag", flex: 0.5, minWidth: 60 },
    { field: "magerr", headerName: "Mag Error", flex: 0.5, minWidth: 60 },
    {
      field: "limiting_mag",
      headerName: "Limiting Mag",
      flex: 0.5,
      minWidth: 60,
    },
    { field: "instrument", headerName: "Instrument", flex: 0.8, minWidth: 100 },
    { field: "filter", headerName: "Filter", flex: 0.6, minWidth: 80 },
    {
      field: "groups",
      headerName: "Currently visible to",
      flex: 2,
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
      colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
      renderCell: ({ row }: any) =>
        row.__detail ? (
          <SpectrumDetail spectrum={row.__source} objID={route.id} />
        ) : (
          <IconButton
            id="expandable-button"
            size="small"
            aria-label="expand row"
            onClick={() =>
              setOpenedSpecRows((prev) =>
                prev.includes(row.id)
                  ? prev.filter((id) => id !== row.id)
                  : [...prev, row.id],
              )
            }
          >
            {openedSpecRows.includes(row.id) ? (
              <KeyboardArrowDownIcon />
            ) : (
              <KeyboardArrowRightIcon />
            )}
          </IconButton>
        ),
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
      renderCell: ({ row }: any) =>
        row.owner && <UserContactLink user={row.owner} />,
    },
    {
      field: "pis",
      headerName: "PI(s)",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: ({ row }: any) => row.external_pi || renderUsers(row.pis),
    },
    {
      field: "reducers",
      headerName: "Reduced by",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: ({ row }: any) =>
        row.external_reducer || renderUsers(row.reducers),
    },
    {
      field: "observers",
      headerName: "Observed by",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: ({ row }: any) =>
        row.external_observer || renderUsers(row.observers),
    },
    {
      field: "reducer_contact",
      headerName: "Reducer contacts",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: ({ row }: any) => renderUsers(row.reducers),
    },
    {
      field: "observer_contact",
      headerName: "Observer contacts",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: ({ row }: any) => renderUsers(row.observers),
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
      renderCell: ({ row }: any) =>
        !row.__detail && <AltdataButton altdata={row.altdata} />,
    },
    {
      field: "delete",
      headerName: "Delete",
      flex: 1,
      minWidth: 90,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) =>
        !row.__detail && <DeleteSpectrumButton specid={row.id} />,
    },
    {
      field: "download",
      headerName: "Download",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) =>
        !row.__detail && <DownloadSpectrumButton spectrum={row} />,
    },
  ];

  const gridProps = {
    autoHeight: true,
    checkboxSelection: true,
    disableRowSelectionOnClick: false,
    pageSizeOptions: [10, 25, 50, 100],
    showToolbar: true,
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Box>
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
        <Typography>
          Select the photometry or spectra you want to share, then the
          groups/users to share them with. Submitting updates the access
          permissions on the data, without saving the source to another group.
        </Typography>
      </Box>
      {!!photRows.length && (
        <StyledDataGrid
          {...gridProps}
          rows={photRows}
          columns={photColumns}
          rowSelectionModel={{
            type: "include",
            ids: new Set(selectedPhotRows),
          }}
          onRowSelectionModelChange={onSelectionChange(
            photRows.map((row: any) => row.id),
            setSelectedPhotRows,
          )}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          slots={{ toolbar: PhotometryGridToolbar }}
        />
      )}
      {!!spectra && (
        <Box data-testid="spectrum-table">
          <StyledDataGrid
            {...gridProps}
            rows={specDisplayRows}
            columns={specColumns}
            getRowHeight={({ model }: any) => (model.__detail ? "auto" : null)}
            columnBufferPx={3000}
            isRowSelectable={({ row }: any) => !row.__detail}
            rowSelectionModel={{
              type: "include",
              ids: new Set(selectedSpecRows),
            }}
            onRowSelectionModelChange={onSelectionChange(
              specRows.map((row: any) => row.id),
              setSelectedSpecRows,
            )}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
              columns: {
                columnVisibilityModel: {
                  reducer_contact: false,
                  observer_contact: false,
                },
              },
            }}
            slots={{ toolbar: SpectrumGridToolbar }}
          />
        </Box>
      )}
      <Box
        component="form"
        onSubmit={handleSubmit(onSubmit)}
        sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        {!!errors["groups"] && (
          <FormValidationError message="Please select at least one group/user" />
        )}
        <Controller
          name="groups"
          control={control}
          defaultValue={[]}
          rules={{ validate: (value: any[]) => value.length >= 1 }}
          render={({ field: { onChange, value } }) => (
            <SearchableSelect
              multiple
              id="dataSharingFormGroupsSelect"
              label="Select Groups/Users"
              options={groups}
              value={value}
              onChange={(data: any) => onChange(data)}
              getOptionLabel={(group: any) => group.name}
              filterSelectedOptions
              error={!!errors["groups"]}
              sx={{ width: "20rem" }}
            />
          )}
        />
        <Box>
          <Button
            primary
            type="submit"
            name="submitShareButton"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Sharing..." : "Submit"}
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default withRouter(ShareDataForm);

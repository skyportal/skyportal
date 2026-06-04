import { useState } from "react";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import { Link } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import InstrumentForm from "./InstrumentForm";
import * as instrumentActions from "../../ducks/instrument";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map are not server-sortable.
const SERVER_SORT_FIELD: Record<string, string> = {
  id: "id",
  instrument_name: "instrument_name",
  telescope_name: "telescope_name",
  Latitude: "Latitude",
  Longitude: "Longitude",
  filters: "filters",
  API_classname: "API_classname",
  API_classname_obsplan: "API_classname_obsplan",
  Band: "Band",
  Type: "Type",
  "FOV Region?": "FOV Region?",
  Fields: "Fields",
};

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  instrumentManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

interface InstrumentTableProps {
  title?: string;
  instruments: any[];
  telescopes?: any[];
  deletePermission?: boolean;
  sortingCallback?: ((...a: any[]) => void) | null;
  paginateCallback?: ((...a: any[]) => void) | null;
  totalMatches?: number;
  numPerPage?: number;
  telescopeInfo?: boolean;
  fixedHeader?: boolean;
}

const InstrumentTable = ({
  title = "Instruments",
  instruments,
  telescopes,
  deletePermission,
  sortingCallback = null,
  paginateCallback = null,
  totalMatches = 0,
  numPerPage = 10,
  telescopeInfo = true,
  fixedHeader = false,
}: InstrumentTableProps) => {
  const { classes } = useStyles() as any;
  const dispatch = useAppDispatch();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [instrumentToEditDelete, setInstrumentToEditDelete] =
    useState<any>(null);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [searchText, setSearchText] = useState("");

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openEditDialog = (id: any) => {
    setEditDialogOpen(true);
    setInstrumentToEditDelete(id);
  };
  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setInstrumentToEditDelete(null);
  };

  const openDeleteDialog = (id: any) => {
    setDeleteDialogOpen(true);
    setInstrumentToEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setInstrumentToEditDelete(null);
  };

  const deleteInstrument = () => {
    dispatch(instrumentActions.deleteInstrument(instrumentToEditDelete)).then(
      (result: any) => {
        if (result.status === "success") {
          dispatch(showNotification("Instrument deleted"));
          closeDeleteDialog();
        }
      },
    );
  };

  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);

  const renderInstrumentID = (params: any) => {
    const instrument = params.row;
    return (
      <div>
        {instrument?.log_exists ? (
          <>
            <Link
              to={`/instrument/${instrument.id}`}
              role="link"
              className={classes.hover}
            >
              {instrument ? instrument.id : ""}
            </Link>
          </>
        ) : (
          <>{instrument ? instrument.id : ""}</>
        )}
      </div>
    );
  };

  const renderInstrumentName = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.name : ""}</div>;
  };

  const renderTelescopeName = (params: any) => {
    const instrument = params.row;
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t: any) => t.id === telescope_id)[0];
    return <div>{telescope ? telescope.nickname : ""}</div>;
  };

  const renderTelescopeLat = (params: any) => {
    const instrument = params.row;
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t: any) => t.id === telescope_id)[0];
    return <div>{telescope ? telescope.lat : ""}</div>;
  };

  const renderTelescopeLon = (params: any) => {
    const instrument = params.row;
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t: any) => t.id === telescope_id)[0];
    return <div>{telescope ? telescope.lon : ""}</div>;
  };

  const renderFilters = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.filters.join("\n") : ""}</div>;
  };

  const renderAPIClassname = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.api_classname : ""}</div>;
  };

  const renderAPIClassnameObsPlan = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.api_classname_obsplan : ""}</div>;
  };

  const renderBand = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.band : ""}</div>;
  };

  const renderType = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.type : ""}</div>;
  };

  const renderRegion = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.region_summary : ""}</div>;
  };

  const renderFields = (params: any) => {
    const instrument = params.row;
    return <div>{instrument ? instrument.number_of_fields : ""}</div>;
  };

  const renderLogs = (params: any) => {
    const instrument = params.row;
    return (
      <div>
        <Button
          key={instrument.id}
          id="logs_button"
          component={Link}
          to={`/instrument/${instrument.id}`}
        >
          Logs
        </Button>
      </div>
    );
  };

  const renderManage = (params: any) => {
    if (!deletePermission) {
      return null;
    }
    const instrument = params.row;
    return (
      <div className={classes.instrumentManage}>
        <Button
          id={`edit_button_${instrument.id}`}
          onClick={() => openEditDialog(instrument.id)}
          disabled={!deletePermission}
        >
          <EditIcon />
        </Button>
        <Button
          id={`delete_button_${instrument.id}`}
          onClick={() => openDeleteDialog(instrument.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const handleSearchChange = (text: string) => {
    if (!paginateCallback) return;
    const data = { name: text };
    paginateCallback(1, rowsPerPage, {}, data);
  };

  const currentSortOrder = () =>
    sortModel.length
      ? {
          name: SERVER_SORT_FIELD[sortModel[0].field] || sortModel[0].field,
          direction: sortModel[0].sort,
        }
      : {};

  const handlePaginationModelChange = (model: any) => {
    if (!paginateCallback) return;
    setRowsPerPage(model.pageSize);
    paginateCallback(model.page + 1, model.pageSize, currentSortOrder());
  };

  const handleSortModelChange = (model: any) => {
    if (!paginateCallback || !sortingCallback) return;
    setSortModel(model);
    if (!model.length) {
      paginateCallback(1, rowsPerPage, {});
      return;
    }
    const { field, sort } = model[0];
    sortingCallback({
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const columns: any[] = [
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
      renderCell: renderInstrumentID,
    },
    {
      field: "instrument_name",
      headerName: "Instrument Name",
      flex: 1,
      minWidth: 140,
      renderCell: renderInstrumentName,
    },
  ];
  if (telescopeInfo === true) {
    columns.push({
      field: "telescope_name",
      headerName: "Telescope Name",
      flex: 1,
      minWidth: 140,
      renderCell: renderTelescopeName,
    });
    columns.push({
      field: "Latitude",
      headerName: "Latitude",
      flex: 1,
      minWidth: 100,
      renderCell: renderTelescopeLat,
    });
    columns.push({
      field: "Longitude",
      headerName: "Longitude",
      flex: 1,
      minWidth: 100,
      renderCell: renderTelescopeLon,
    });
  }

  columns.push({
    field: "filters",
    headerName: "Filters",
    flex: 1,
    minWidth: 100,
    renderCell: renderFilters,
  });
  columns.push({
    field: "API_classname",
    headerName: "API Classname",
    flex: 1,
    minWidth: 140,
    renderCell: renderAPIClassname,
  });
  columns.push({
    field: "API_classname_obsplan",
    headerName: "API Observation Plan Classname",
    flex: 1,
    minWidth: 200,
    renderCell: renderAPIClassnameObsPlan,
  });
  columns.push({
    field: "Band",
    headerName: "Band",
    flex: 1,
    minWidth: 90,
    renderCell: renderBand,
  });
  columns.push({
    field: "Type",
    headerName: "Type",
    flex: 1,
    minWidth: 90,
    renderCell: renderType,
  });
  columns.push({
    field: "FOV Region?",
    headerName: "FOV Region?",
    flex: 1,
    minWidth: 120,
    renderCell: renderRegion,
  });
  columns.push({
    field: "Fields",
    headerName: "Fields",
    flex: 1,
    minWidth: 90,
    renderCell: renderFields,
  });
  columns.push({
    field: "logs",
    headerName: " ",
    flex: 1,
    minWidth: 90,
    sortable: false,
    filterable: false,
    renderCell: renderLogs,
  });
  columns.push({
    field: "manage",
    headerName: " ",
    flex: 1,
    minWidth: 120,
    sortable: false,
    filterable: false,
    renderCell: renderManage,
  });

  const CustomToolbar = function InstrumentTableToolbar() {
    return (
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <TextField
          variant="standard"
          size="small"
          placeholder="Search"
          value={searchText}
          onChange={(event) => {
            setSearchText(event.target.value);
            handleSearchChange(event.target.value);
          }}
        />
        <IconButton
          name="new_instrument"
          onClick={() => {
            openNewDialog();
          }}
        >
          <AddIcon />
        </IconButton>
      </GridToolbarContainer>
    );
  };

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
          {title}
        </Typography>
        <Box
          sx={
            fixedHeader
              ? { height: "calc(100vh - 148px)", width: "100%" }
              : { width: "100%" }
          }
        >
          <StyledDataGrid
            autoHeight={!fixedHeader}
            rows={instruments || []}
            columns={columns}
            getRowId={(row: any) => row.id}
            paginationMode="server"
            sortingMode="server"
            rowCount={totalMatches}
            paginationModel={{ page: 0, pageSize: rowsPerPage }}
            onPaginationModelChange={handlePaginationModelChange}
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            disableColumnFilter
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
        <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
          <DialogTitle>New Instrument</DialogTitle>
          <DialogContent dividers>
            <InstrumentForm onClose={closeNewDialog} />
          </DialogContent>
        </Dialog>
        <Dialog
          open={editDialogOpen && instrumentToEditDelete !== null}
          onClose={closeEditDialog}
          maxWidth="md"
        >
          <DialogTitle>
            {`Edit ${
              instruments.find((i: any) => i.id === instrumentToEditDelete)
                ?.name
            } instrument`}
          </DialogTitle>
          <DialogContent dividers>
            <InstrumentForm
              onClose={closeEditDialog}
              instrumentId={instrumentToEditDelete}
            />
          </DialogContent>
        </Dialog>
        <ConfirmDeletionDialog
          deleteFunction={deleteInstrument}
          dialogOpen={deleteDialogOpen}
          closeDialog={closeDeleteDialog}
          resourceName="instrument"
        />
      </Paper>
    </div>
  );
};

export default InstrumentTable;

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";

import { showNotification } from "baselayer/components/Notifications";
import { useDeleteInstrumentMutation } from "../../ducks/instrument";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import { useAppDispatch } from "../../types";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import InstrumentForm from "./InstrumentForm";
import Button from "../Button";
import Paper from "../Paper";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

interface InstrumentTableProps {
  title?: string;
  instruments: any[];
  telescopes?: any[];
  managePermission?: boolean;
  telescopeInfo?: boolean;
  fixedHeader?: boolean;
}

const InstrumentTable = ({
  title = "Instruments",
  instruments,
  telescopes,
  managePermission = false,
  telescopeInfo = true,
  fixedHeader = false,
}: InstrumentTableProps) => {
  const dispatch = useAppDispatch();
  const [deleteInstrumentMutation] = useDeleteInstrumentMutation();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [instrumentToManage, setInstrumentToManage] = useState<number | null>(
    null,
  );

  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setInstrumentToManage(null);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setInstrumentToManage(null);
  };

  const deleteInstrument = async () => {
    try {
      await deleteInstrumentMutation(instrumentToManage!).unwrap();
      dispatch(showNotification("Instrument deleted"));
      closeDeleteDialog();
    } catch {
      // error notification handled by the base query
    }
  };

  // Enrich instruments with telescope info and combined API classnames so the
  // table can search/sort/filter on those fields client-side.
  const enrichedInstruments = useMemo(() => {
    const telescopeById = new Map(telescopes?.map((t) => [t.id, t]) || []);
    return (instruments || []).map((instrument) => {
      const telescope = telescopeById.get(instrument.telescope_id);
      return {
        ...instrument,
        telescope_nickname: telescope?.nickname || "",
        lat: telescope?.lat,
        lon: telescope?.lon,
        api_classnames: [
          instrument.api_classname,
          instrument.api_classname_obsplan,
        ]
          .filter(Boolean)
          .join(" "),
      };
    });
  }, [instruments, telescopes]);

  const renderInstrumentName = (params: any) => {
    const instrument = params.row;
    return (
      <Link to={`/instrument/${instrument.id}`}>{instrument?.name || ""}</Link>
    );
  };

  const renderTelescopeNickname = (params: any) => {
    const instrument = params.row;
    return (
      <Link to={`/telescope/${instrument?.telescope_id}`}>
        {instrument?.telescope_nickname || ""}
      </Link>
    );
  };

  const renderFilters = (params: any) => {
    const filters = params.row.filters;
    return filters?.map((filter: any) => <div key={filter}>{filter}</div>);
  };

  const renderAPIClassnames = (params: any) => {
    const { api_classname, api_classname_obsplan } = params.row;
    if (!api_classname && !api_classname_obsplan) return null;

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "2px",
          alignItems: "start",
        }}
      >
        {api_classname && (
          <Tooltip title="API for Follow-up Requests" placement="top">
            <Chip label={api_classname} />
          </Tooltip>
        )}
        {api_classname_obsplan && (
          <Tooltip title="API for Observation Plan" placement="bottom">
            <Chip label={api_classname_obsplan} />
          </Tooltip>
        )}
      </div>
    );
  };

  const renderManage = (params: any) => {
    const instrument = params.row;
    return (
      <div style={{ display: "flex" }}>
        <Button
          onClick={() => {
            setEditDialogOpen(true);
            setInstrumentToManage(instrument.id);
          }}
        >
          <EditIcon />
        </Button>
        <Button
          color="error"
          onClick={() => {
            setDeleteDialogOpen(true);
            setInstrumentToManage(instrument.id);
          }}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns: any[] = [
    { field: "id", headerName: "ID" },
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 140,
      renderCell: renderInstrumentName,
    },
    ...(telescopeInfo
      ? [
          {
            field: "telescope_nickname",
            headerName: "Telescope",
            flex: 1,
            minWidth: 140,
            renderCell: renderTelescopeNickname,
          },
          { field: "lat", headerName: "Latitude", flex: 1, minWidth: 100 },
          { field: "lon", headerName: "Longitude", flex: 1, minWidth: 100 },
        ]
      : []),
    {
      field: "filters",
      headerName: "Filters",
      flex: 1,
      minWidth: 100,
      renderCell: renderFilters,
    },
    {
      field: "api_classnames",
      headerName: "API Classnames",
      flex: 1,
      minWidth: 160,
      renderCell: renderAPIClassnames,
    },
    { field: "band", headerName: "Band", flex: 1, minWidth: 90 },
    { field: "type", headerName: "Type", flex: 1, minWidth: 90 },
    {
      field: "region_summary",
      headerName: "FOV Region?",
      flex: 1,
      minWidth: 120,
    },
    {
      field: "number_of_fields",
      headerName: "Fields",
      flex: 1,
      minWidth: 90,
    },
    ...(managePermission
      ? [
          {
            field: "manage",
            headerName: " ",
            minWidth: 120,
            sortable: false,
            filterable: false,
            renderCell: renderManage,
          },
        ]
      : []),
  ];

  const CustomToolbar = function InstrumentTableToolbar() {
    return (
      <DataGridToolbar>
        <IconButton
          name="new_instrument"
          onClick={() => setNewDialogOpen(true)}
        >
          <AddIcon />
        </IconButton>
      </DataGridToolbar>
    );
  };

  return (
    <Paper>
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
          rows={enrichedInstruments}
          columns={columns}
          getRowId={(row: any) => row.id}
          pageSizeOptions={PAGE_SIZE_OPTIONS}
          initialState={{
            columns: { columnVisibilityModel: { id: false } },
            pagination: { paginationModel: { pageSize: 25, page: 0 } },
          }}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Box>
      <Dialog
        open={newDialogOpen}
        onClose={() => setNewDialogOpen(false)}
        maxWidth="md"
      >
        <DialogTitle>New Instrument</DialogTitle>
        <DialogContent dividers>
          <InstrumentForm onClose={() => setNewDialogOpen(false)} />
        </DialogContent>
      </Dialog>
      <Dialog
        open={editDialogOpen && instrumentToManage !== null}
        onClose={closeEditDialog}
        maxWidth="md"
      >
        <DialogTitle>
          Edit{" "}
          {enrichedInstruments.find((i) => i.id === instrumentToManage)?.name}{" "}
          instrument
        </DialogTitle>
        <DialogContent dividers>
          <InstrumentForm
            onClose={closeEditDialog}
            instrumentId={instrumentToManage}
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
  );
};

export default InstrumentTable;

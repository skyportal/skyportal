import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import AddIcon from "@mui/icons-material/Add";

import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT,
} from "../StyledDataGrid";
import ExpandableCell from "../ExpandableCell";
import InstrumentForm from "./InstrumentForm";
import { useIsReadOnly } from "../../ducks/profile";

interface InstrumentTableProps {
  title?: string;
  instruments: any[];
  telescopes?: any[];
  telescopeInfo?: boolean;
  fixedHeader?: boolean;
}

const InstrumentTable = ({
  title = "Instruments",
  instruments,
  telescopes,
  telescopeInfo = true,
  fixedHeader = false,
}: InstrumentTableProps) => {
  const navigate = useNavigate();
  const isReadOnly = useIsReadOnly();
  const [newDialogOpen, setNewDialogOpen] = useState(false);

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

  const renderTelescopeNickname = (params: any) => {
    const instrument = params.row;
    return (
      <Link
        to={`/telescope/${instrument?.telescope_id}`}
        onClick={(event) => event.stopPropagation()}
      >
        {instrument?.telescope_nickname || ""}
      </Link>
    );
  };

  const renderFilters = (params: any) => (
    <ExpandableCell
      maxVisible={6}
      items={(params.row.filters ?? []).map((filter: string) => (
        <Chip key={filter} label={filter} size="small" />
      ))}
    />
  );

  const renderAPIClassnames = (params: any) => {
    const { api_classname, api_classname_obsplan } = params.row;
    if (!api_classname && !api_classname_obsplan) return null;

    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "start",
          gap: 0.5,
        }}
      >
        {api_classname && (
          <Tooltip title="API for Follow-up Requests" placement="top">
            <Chip label={api_classname} size="small" />
          </Tooltip>
        )}
        {api_classname_obsplan && (
          <Tooltip title="API for Observation Plan" placement="bottom">
            <Chip label={api_classname_obsplan} size="small" />
          </Tooltip>
        )}
      </Box>
    );
  };

  const columns: any[] = [
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
    },
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      minWidth: 140,
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
      flex: 2,
      minWidth: 200,
      renderCell: renderFilters,
    },
    {
      field: "api_classnames",
      headerName: "API Classnames",
      flex: 1,
      minWidth: 160,
      renderCell: renderAPIClassnames,
    },
    { field: "band", headerName: "Band", flex: 0.6, minWidth: 80 },
    {
      field: "type",
      headerName: "Type",
      flex: 0.8,
      minWidth: 150,
      renderCell: ({ value }: any) =>
        value && <Chip label={value} size="small" variant="outlined" />,
    },
    {
      field: "region_summary",
      headerName: "FOV Region?",
      flex: 1,
      minWidth: 120,
    },
    {
      field: "number_of_fields",
      headerName: "Fields",
      flex: 0.5,
      minWidth: 70,
    },
  ];

  const CustomToolbar = function InstrumentTableToolbar() {
    return (
      <DataGridToolbar title={title}>
        {!isReadOnly && (
          <IconButton
            name="new_instrument"
            data-testid="tour-instruments-new"
            onClick={() => setNewDialogOpen(true)}
          >
            <AddIcon />
          </IconButton>
        )}
      </DataGridToolbar>
    );
  };

  return (
    <>
      <StyledDataGrid
        height={fixedHeader ? FULL_PAGE_HEIGHT : "auto"}
        rows={enrichedInstruments}
        columns={columns}
        getRowHeight={() => "auto"}
        sx={{ "& .MuiDataGrid-row": { cursor: "pointer" } }}
        onRowClick={({ row }: any) => navigate(`/instrument/${row.id}`)}
        pageSizeOptions={[25, 50, 100, { value: -1, label: "All" }]}
        initialState={{
          columns: {
            columnVisibilityModel: {
              id: false,
              lat: false,
              lon: false,
              region_summary: false,
              number_of_fields: false,
            },
          },
          pagination: { paginationModel: { pageSize: -1 } },
        }}
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
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
    </>
  );
};

export default InstrumentTable;

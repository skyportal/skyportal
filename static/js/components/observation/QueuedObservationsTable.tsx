import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import DownloadIcon from "@mui/icons-material/Download";
import FilterListIcon from "@mui/icons-material/FilterList";

import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT_WITH_TABS,
} from "../StyledDataGrid";
import ObservationFilterForm from "./ObservationFilterForm";
import NewAPIQueuedObservation from "./NewAPIQueuedObservation";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useHasPermission } from "../../ducks/profile";

const SERVER_SORT_FIELD: Record<string, string> = {
  instrument_name: "instrument_name",
  field_id: "field_id",
};

interface QueuedObservationsTableProps {
  observations: any[];
  totalMatches?: number;
  downloadCallback: (...a: any[]) => any;
  handleTableChange?: any;
  handleFilterSubmit?: any;
  pageNumber?: number;
  numPerPage?: number;
  serverSide?: boolean;
  fixedHeader?: boolean;
  filterModel?: any;
  onFilterModelChange?: ((model: any) => void) | undefined;
}

const QueuedObservationsTable = ({
  observations,
  totalMatches = 0,
  downloadCallback,
  handleTableChange = false,
  handleFilterSubmit = false,
  pageNumber = 1,
  numPerPage = 25,
  serverSide = true,
  fixedHeader = false,
  filterModel,
  onFilterModelChange,
}: QueuedObservationsTableProps) => {
  const canUploadData = useHasPermission("Upload data");

  const { data: instrumentList = [] } = useGetInstrumentsQuery();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  const [sortModel, setSortModel] = useState<any[]>([]);

  const instrumentsLookup: Record<string, any> = {};
  if (instrumentList) {
    instrumentList.forEach((instrument: any) => {
      instrumentsLookup[instrument.id] = instrument;
    });
  }

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const emitTableChange = (action: any, model: any, currentSort: any) => {
    if (typeof handleTableChange !== "function") {
      return;
    }
    handleTableChange(action, {
      page: model.page,
      rowsPerPage: model.pageSize,
      sortOrder: currentSort,
    });
  };

  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    const currentSort = sortModel.length
      ? {
          name: SERVER_SORT_FIELD[sortModel[0].field] || sortModel[0].field,
          direction: sortModel[0].sort,
        }
      : { direction: "none" };
    emitTableChange("changePage", model, currentSort);
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    const paginationModel = { page: pageNumber - 1, pageSize: rowsPerPage };
    if (!model.length) {
      emitTableChange("sort", paginationModel, { direction: "none" });
      return;
    }
    const { field, sort } = model[0];
    emitTableChange("sort", paginationModel, {
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const columns: any[] = [
    {
      field: "telescope_name",
      headerName: "Telescope",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        instrumentsLookup[row.instrument_id]?.telescope?.name || "",
      renderCell: (params: any) => {
        const instrument = instrumentsLookup[params.row.instrument_id] || null;
        if (!instrument) {
          return <div>Loading...</div>;
        }
        return <div>{instrument?.telescope?.name || ""}</div>;
      },
    },
    {
      field: "instrument_name",
      headerName: "Instrument",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        instrumentsLookup[row.instrument_id]?.name || "",
      renderCell: (params: any) => {
        const instrument = instrumentsLookup[params.row.instrument_id] || null;
        if (!instrument) {
          return <div>Loading...</div>;
        }
        return <div>{instrument?.name || ""}</div>;
      },
    },
    {
      field: "queue_name",
      headerName: "Queue name",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
    },
    {
      field: "field_id",
      headerName: "Field ID",
      flex: 1,
      minWidth: 100,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.field ? row.field?.field_id?.toFixed(0) : "",
    },
    {
      field: "ra",
      headerName: "Right Ascension",
      flex: 1,
      minWidth: 130,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.field ? row.field?.ra?.toFixed(5) : "",
    },
    {
      field: "dec",
      headerName: "Declination",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.field ? row.field?.dec?.toFixed(5) : "",
    },
    {
      field: "obstime",
      headerName: "Observation time",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "filt",
      headerName: "Filter",
      flex: 1,
      minWidth: 90,
    },
    {
      field: "exposure_time",
      headerName: "Exposure time [s]",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "validity_window_start",
      headerName: "Validity Window [start]",
      flex: 1,
      minWidth: 180,
    },
    {
      field: "validity_window_end",
      headerName: "Validity Window [end]",
      flex: 1,
      minWidth: 180,
    },
  ];

  const handleDownload = () => {
    const renderTelescopeDownload = (observation: any) => {
      const instrument = instrumentsLookup[observation.instrument_id] || null;
      if (!instrument) {
        return "";
      }
      return instrument?.telescope?.name || "";
    };
    const renderInstrumentDownload = (observation: any) => {
      const instrument = instrumentsLookup[observation.instrument_id] || null;
      if (!instrument) {
        return "";
      }
      return instrument?.name || "";
    };
    const renderFieldIDDownload = (observation: any) =>
      observation.field ? observation.field?.field_id : "";
    const renderRADownload = (observation: any) =>
      observation.field ? observation.field?.ra : "";
    const renderDeclinationDownload = (observation: any) =>
      observation.field ? observation.field?.dec : "";

    downloadCallback().then((data: any) => {
      if (!data?.length) {
        return;
      }
      const head = [
        "telescope_name",
        "instrument_name",
        "queue_name",
        "field_id",
        "ra",
        "dec",
        "obstime",
        "filt",
        "exposure_time",
        "validity_window_start",
        "validity_window_end",
      ];
      const rows = data.map((x: any) =>
        [
          renderTelescopeDownload(x),
          renderInstrumentDownload(x),
          x.queue_name,
          renderFieldIDDownload(x),
          renderRADownload(x),
          renderDeclinationDownload(x),
          x.obstime,
          x.filt,
          x.exposure_time,
          x.validity_window_start,
          x.validity_window_end,
        ].join(","),
      );
      const result = `${head.join(",")}\n${rows.join("\n")}`;
      const blob = new Blob([result], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "observations.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    });
  };

  const CustomToolbar = () => (
    <DataGridToolbar title="Queued Observations" showExport={false}>
      <Tooltip title="Filter Table">
        <IconButton
          size="small"
          data-testid="Filter Table-iconButton"
          onClick={() => setFilterOpen(true)}
        >
          <FilterListIcon />
        </IconButton>
      </Tooltip>
      {canUploadData && (
        <IconButton
          name="new_queued_observation"
          size="small"
          onClick={() => {
            openNewDialog();
          }}
        >
          <AddIcon />
        </IconButton>
      )}
      <Tooltip title="Download CSV">
        <IconButton
          size="small"
          aria-label="Download CSV"
          data-testid="download-queued-observations-button"
          onClick={handleDownload}
        >
          <DownloadIcon />
        </IconButton>
      </Tooltip>
    </DataGridToolbar>
  );

  return (
    <>
      <StyledDataGrid
        height={fixedHeader ? FULL_PAGE_HEIGHT_WITH_TABS : "60vh"}
        rows={observations}
        columns={columns}
        getRowId={(row: any) =>
          row.id ?? `${row.instrument_id}_${row.queue_name}_${row.obstime}`
        }
        paginationMode={serverSide ? "server" : "client"}
        sortingMode={serverSide ? "server" : "client"}
        rowCount={totalMatches}
        paginationModel={{
          page: pageNumber - 1,
          pageSize: rowsPerPage,
        }}
        onPaginationModelChange={handlePaginationModelChange}
        sortModel={sortModel}
        onSortModelChange={handleSortModelChange}
        filterModel={filterModel}
        onFilterModelChange={onFilterModelChange}
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
        <DialogTitle>Add Queued Observations (from API)</DialogTitle>
        <DialogContent dividers>
          <NewAPIQueuedObservation onClose={closeNewDialog} />
        </DialogContent>
      </Dialog>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>
          <ObservationFilterForm handleFilterSubmit={handleFilterSubmit} />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default QueuedObservationsTable;

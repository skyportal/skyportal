import { useState } from "react";
import { useNavigate } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import DownloadIcon from "@mui/icons-material/Download";
import FilterListIcon from "@mui/icons-material/FilterList";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT_WITH_TABS,
} from "../StyledDataGrid";
import ObservationFilterForm from "./ObservationFilterForm";
import NewObservation from "./NewObservation";
import NewAPIObservation from "./NewAPIObservation";

import {
  useCheckSourceMutation,
  useSaveSourceMutation,
} from "../../ducks/source";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useHasPermission } from "../../ducks/profile";

const SERVER_SORT_FIELD: Record<string, string> = {
  instrument_name: "instrument_name",
  seeing: "seeing",
  limmag: "limmag",
};

interface ExecutedObservationsTableProps {
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

const ExecutedObservationsTable = ({
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
}: ExecutedObservationsTableProps) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const canUploadData = useHasPermission("Upload data");
  const [checkSource] = useCheckSourceMutation();
  const [saveSource] = useSaveSourceMutation();

  const { data: instrumentList = [] } = useGetInstrumentsQuery();

  // Anchor by position: the inline toolbar slot remounts each render, detaching an el anchor.
  const [addMenuPos, setAddMenuPos] = useState<{
    top: number;
    left: number;
  } | null>(null);
  const [newDialogFromFileOpen, setNewDialogFromFileOpen] = useState(false);
  const [newDialogFromAPIOpen, setNewDialogFromAPIOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState<any>(null);

  const instrumentsLookup: Record<string, any> = {};
  if (instrumentList) {
    instrumentList.forEach((instrument: any) => {
      instrumentsLookup[instrument.id] = instrument;
    });
  }

  const handleClose = () => {
    setAddMenuPos(null);
  };

  const openNewFromFileDialog = () => {
    setAddMenuPos(null);
    setNewDialogFromFileOpen(true);
  };
  const openNewFromAPIDialog = () => {
    setAddMenuPos(null);
    setNewDialogFromAPIOpen(true);
  };
  const closeNewFromFileDialog = () => {
    setNewDialogFromFileOpen(false);
  };
  const closeNewFromAPIDialog = () => {
    setNewDialogFromAPIOpen(false);
  };

  const handleSave = async (formData: any) => {
    setIsSaving(formData.id);
    try {
      const data: any = await checkSource({
        id: formData.id,
        params: formData,
      }).unwrap();
      if (data?.source_exists === true) {
        dispatch(showNotification(data.message, "error"));
      } else {
        await saveSource(formData).unwrap();
        dispatch(showNotification("Source saved"));
        navigate(`/source/${formData.id}`);
      }
    } catch {
      // error notification handled by the baseQuery
    }
    setIsSaving(null);
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
      renderCell: ({ row, value }: any) =>
        instrumentsLookup[row.instrument_id] ? value : "Loading...",
    },
    {
      field: "instrument_name",
      headerName: "Instrument",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        instrumentsLookup[row.instrument_id]?.name || "",
      renderCell: ({ row, value }: any) =>
        instrumentsLookup[row.instrument_id] ? value : "Loading...",
    },
    {
      field: "observation_id",
      headerName: " Observation ID",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "field_id",
      headerName: "Field ID",
      flex: 1,
      minWidth: 100,
      sortable: false,
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
      field: "target_name",
      headerName: "Target Name",
      flex: 1,
      minWidth: 120,
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
      field: "airmass",
      headerName: "Airmass",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
    },
    {
      field: "seeing",
      headerName: "Seeing [arcsec]",
      flex: 1,
      minWidth: 130,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.seeing ? row.seeing.toFixed(1) : "",
    },
    {
      field: "limmag",
      headerName: "Limiting magnitude",
      flex: 1,
      minWidth: 150,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.limmag ? row.limmag.toFixed(2) : "",
    },
    {
      field: "save_source",
      headerName: "Save Source",
      flex: 1,
      minWidth: 130,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) => {
        if (!row.target_name || !canUploadData) return null;
        const formData = {
          id: row.target_name.replace(/ /g, "_"),
          ra: row.field.ra,
          dec: row.field.dec,
        };
        if (isSaving === formData.id) return <CircularProgress />;
        return (
          <Button primary onClick={() => handleSave(formData)} size="small">
            Save Source
          </Button>
        );
      },
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
        "observation_id",
        "field_id",
        "ra",
        "dec",
        "target_name",
        "obstime",
        "filt",
        "exposure_time",
        "airmass",
        "seeing",
        "limmag",
      ];
      const rows = data.map((x: any) =>
        [
          renderTelescopeDownload(x),
          renderInstrumentDownload(x),
          x.observation_id,
          renderFieldIDDownload(x),
          renderRADownload(x),
          renderDeclinationDownload(x),
          x.target_name,
          x.obstime,
          x.filt,
          x.exposure_time,
          x.airmass,
          x.seeing,
          x.limmag,
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
    <DataGridToolbar title="Executed Observations" showExport={false}>
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
          name="new_executed_observation"
          size="small"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            setAddMenuPos({ top: rect.bottom, left: rect.left });
          }}
        >
          <AddIcon />
        </IconButton>
      )}
      <Tooltip title="Download CSV">
        <IconButton
          size="small"
          aria-label="Download CSV"
          data-testid="download-executed-observations-button"
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
          row.id ?? `${row.instrument_id}_${row.observation_id}`
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
      <Menu
        open={Boolean(addMenuPos)}
        onClose={handleClose}
        anchorReference="anchorPosition"
        anchorPosition={addMenuPos ?? undefined}
      >
        <MenuItem onClick={openNewFromFileDialog}>Add from File</MenuItem>
        <MenuItem onClick={openNewFromAPIDialog}>Add from API</MenuItem>
      </Menu>
      <Dialog
        open={newDialogFromFileOpen}
        onClose={closeNewFromFileDialog}
        maxWidth="md"
      >
        <DialogTitle>Add Executed Observations (from file)</DialogTitle>
        <DialogContent dividers>
          <NewObservation onClose={closeNewFromFileDialog} />
        </DialogContent>
      </Dialog>
      <Dialog
        open={newDialogFromAPIOpen}
        onClose={closeNewFromAPIDialog}
        maxWidth="md"
      >
        <DialogTitle>Add Executed Observations (from API)</DialogTitle>
        <DialogContent dividers>
          <NewAPIObservation onClose={closeNewFromAPIDialog} />
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

export default ExecutedObservationsTable;

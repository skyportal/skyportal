import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import AddIcon from "@mui/icons-material/Add";
import DownloadIcon from "@mui/icons-material/Download";
import FilterListIcon from "@mui/icons-material/FilterList";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Grow from "@mui/material/Grow";
import Popper from "@mui/material/Popper";
import MenuList from "@mui/material/MenuList";
import MenuItem from "@mui/material/MenuItem";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarQuickFilter,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ObservationFilterForm from "./ObservationFilterForm";
import NewObservation from "./NewObservation";
import NewAPIObservation from "./NewAPIObservation";

import { checkSource, saveSource } from "../../ducks/source";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map are not server-sortable.
const SERVER_SORT_FIELD: Record<string, string> = {
  instrument_name: "instrument_name",
  seeing: "seeing",
  limmag: "limmag",
};

const useStyles = makeStyles()((theme: any) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
}));

interface ExecutedObservationsTableProps {
  observations: any[];
  totalMatches?: number;
  downloadCallback: (...a: any[]) => any;
  handleTableChange?: any;
  handleFilterSubmit?: any;
  pageNumber?: number;
  numPerPage?: number;
  serverSide?: boolean;
}

const ExecutedObservationsTable = ({
  observations,
  totalMatches = 0,
  downloadCallback,
  handleTableChange = false,
  handleFilterSubmit = false,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = true,
}: ExecutedObservationsTableProps) => {
  const { classes } = useStyles();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();

  const { instrumentList } = useAppSelector((state) => state.instruments);

  const [open, setOpen] = useState(false);
  const [newDialogFromFileOpen, setNewDialogFromFileOpen] = useState(false);
  const [newDialogFromAPIOpen, setNewDialogFromAPIOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState<any>(null);
  const anchorRef = useRef<any>(null);

  const instrumentsLookup: Record<string, any> = {};
  if (instrumentList) {
    instrumentList.forEach((instrument: any) => {
      instrumentsLookup[instrument.id] = instrument;
    });
  }

  const handleClose = () => {
    setOpen(false);
  };

  const openNewFromFileDialog = () => {
    setOpen(false);
    setNewDialogFromFileOpen(true);
  };
  const openNewFromAPIDialog = () => {
    setOpen(false);
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
    const data: any = await dispatch(checkSource(formData.id, formData));
    if (data.status === "success") {
      if (data.data?.source_exists === true) {
        dispatch(showNotification(data.data.message, "error"));
      } else {
        const result: any = await dispatch(saveSource(formData));
        if (result.status === "success") {
          dispatch(showNotification("Source saved"));
          navigate(`/source/${formData.id}`);
        }
      }
    }
    setIsSaving(null);
  };

  // Synthesize the mui-datatables onTableChange(action, tableState) contract
  // from the DataGrid handlers so callers (ObservationPage) stay unchanged.
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

  const renderSaveSource = (params: any) => {
    const observation = params.row;
    const formData = {
      id: observation.target_name?.replace(/ /g, "_"),
      ra: observation.field.ra,
      dec: observation.field.dec,
    };
    if (!observation.target_name) {
      return <div />;
    }
    return (
      <div className={classes.actionButtons}>
        {isSaving === formData.id ? (
          <div>
            <CircularProgress />
          </div>
        ) : (
          <div>
            <Button
              primary
              onClick={() => {
                handleSave(formData);
              }}
              size="small"
              type="submit"
              data-testid={`saveObservation_${formData.id}`}
            >
              Save Source
            </Button>
          </div>
        )}
      </div>
    );
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
      renderCell: renderSaveSource,
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
      // if there is no data, cancel download
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
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <Tooltip title="Filter Table">
        <IconButton
          size="small"
          data-testid="Filter Table-iconButton"
          onClick={() => setFilterOpen(true)}
        >
          <FilterListIcon />
        </IconButton>
      </Tooltip>
      <IconButton
        name="new_executed_observation"
        size="small"
        ref={anchorRef}
        onClick={() => {
          setOpen(true);
        }}
      >
        <AddIcon />
      </IconButton>
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
      <GridToolbarQuickFilter />
    </GridToolbarContainer>
  );

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" style={{ padding: "0.5rem" }}>
          Executed Observations
        </Typography>
        <Box sx={{ height: "60vh", width: "100%" }}>
          <StyledDataGrid
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
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
        <Popper
          open={open}
          anchorEl={() => anchorRef.current}
          role={undefined}
          transition
          disablePortal
          style={{ zIndex: 1 }}
        >
          {({ TransitionProps, placement }) => (
            <Grow
              {...TransitionProps}
              style={{
                transformOrigin:
                  placement === "bottom" ? "center top" : "center bottom",
              }}
            >
              <Paper>
                <ClickAwayListener onClickAway={handleClose}>
                  <MenuList autoFocusItem={open} id="menu-list-grow">
                    <MenuItem onClick={openNewFromFileDialog}>
                      {" "}
                      Add from File
                    </MenuItem>
                    <MenuItem onClick={openNewFromAPIDialog}>
                      {" "}
                      Add from API
                    </MenuItem>
                  </MenuList>
                </ClickAwayListener>
              </Paper>
            </Grow>
          )}
        </Popper>
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
        <Dialog
          open={filterOpen}
          onClose={() => setFilterOpen(false)}
          fullWidth
        >
          <DialogContent>
            <ObservationFilterForm handleFilterSubmit={handleFilterSubmit} />
          </DialogContent>
        </Dialog>
      </Paper>
    </div>
  );
};

export default ExecutedObservationsTable;

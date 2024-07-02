import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import { Link } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewInstrument from "./NewInstrument";
import ModifyInstrument from "./ModifyInstrument";
import * as instrumentActions from "../../ducks/instrument";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  instrumentManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
      },
    },
  });

const InstrumentTable = ({
  instruments,
  telescopes,
  deletePermission,
  paginateCallback,
  totalMatches,
  numPerPage,
  sortingCallback,
  hideTitle = false,
  telescopeInfo = true,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [instrumentToEditDelete, setInstrumentToEditDelete] = useState(null);

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openEditDialog = (id) => {
    setEditDialogOpen(true);
    setInstrumentToEditDelete(id);
  };
  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setInstrumentToEditDelete(null);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setInstrumentToEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setInstrumentToEditDelete(null);
  };

  const deleteInstrument = () => {
    dispatch(instrumentActions.deleteInstrument(instrumentToEditDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Instrument deleted"));
          closeDeleteDialog();
        }
      },
    );
  };

  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);

  const renderInstrumentID = (dataIndex) => {
    const instrument = instruments[dataIndex];

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

  const renderInstrumentName = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.name : ""}</div>;
  };

  const renderTelescopeName = (dataIndex) => {
    const instrument = instruments[dataIndex];
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];

    return <div>{telescope ? telescope.nickname : ""}</div>;
  };

  const renderTelescopeLat = (dataIndex) => {
    const instrument = instruments[dataIndex];
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];

    return <div>{telescope ? telescope.lat : ""}</div>;
  };

  const renderTelescopeLon = (dataIndex) => {
    const instrument = instruments[dataIndex];
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];

    return <div>{telescope ? telescope.lon : ""}</div>;
  };

  const renderFilters = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.filters.join("\n") : ""}</div>;
  };

  const renderAPIClassname = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.api_classname : ""}</div>;
  };

  const renderAPIClassnameObsPlan = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.api_classname_obsplan : ""}</div>;
  };

  const renderBand = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.band : ""}</div>;
  };

  const renderType = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.type : ""}</div>;
  };

  const renderRegion = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.region_summary : ""}</div>;
  };

  const renderFields = (dataIndex) => {
    const instrument = instruments[dataIndex];

    return <div>{instrument ? instrument.number_of_fields : ""}</div>;
  };

  const renderLogs = (dataIndex) => {
    const instrument = instruments[dataIndex];
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

  const renderManage = (dataIndex) => {
    if (!deletePermission) {
      return null;
    }
    const instrument = instruments[dataIndex];
    return (
      <div className={classes.instrumentManage}>
        <Button
          key={`edit_${instrument.id}`}
          id={`edit_button_${instrument.id}`}
          onClick={() => openEditDialog(instrument.id)}
          disabled={!deletePermission}
        >
          <EditIcon />
        </Button>
        <Button
          key={`delete_${instrument.id}`}
          id={`delete_button_${instrument.id}`}
          onClick={() => openDeleteDialog(instrument.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const handleSearchChange = (searchText) => {
    const data = { name: searchText };
    paginateCallback(1, rowsPerPage, {}, data);
  };

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        setRowsPerPage(tableState.rowsPerPage);
        paginateCallback(
          tableState.page + 1,
          tableState.rowsPerPage,
          tableState.sortOrder,
        );
        break;
      case "sort":
        if (tableState.sortOrder.direction === "none") {
          paginateCallback(1, tableState.rowsPerPage, {});
        } else {
          sortingCallback(tableState.sortOrder);
        }
        break;
      default:
    }
  };

  const columns = [
    {
      name: "id",
      label: "ID",
      options: {
        filter: true,
        // sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrumentID,
      },
    },
    {
      name: "instrument_name",
      label: "Instrument Name",
      options: {
        filter: true,
        // sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrumentName,
      },
    },
  ];
  if (telescopeInfo === true) {
    columns.push({
      name: "telescope_name",
      label: "Telescope Name",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescopeName,
      },
    });
    columns.push({
      name: "Latitude",
      label: "Latitude",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescopeLat,
      },
    });
    columns.push({
      name: "Longitude",
      label: "Longitude",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescopeLon,
      },
    });
  }

  columns.push({
    name: "filters",
    label: "Filters",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderFilters,
    },
  });
  columns.push({
    name: "API_classname",
    label: "API Classname",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderAPIClassname,
    },
  });
  columns.push({
    name: "API_classname_obsplan",
    label: "API Observation Plan Classname",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderAPIClassnameObsPlan,
    },
  });
  columns.push({
    name: "Band",
    label: "Band",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderBand,
    },
  });
  columns.push({
    name: "Type",
    label: "Type",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderType,
    },
  });
  columns.push({
    name: "FOV Region?",
    label: "FOV Region?",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderRegion,
    },
  });
  columns.push({
    name: "Fields",
    label: "Fields",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderFields,
    },
  });
  columns.push({
    name: "logs",
    label: " ",
    options: {
      customBodyRenderLite: renderLogs,
    },
  });
  columns.push({
    name: "manage",
    label: " ",
    options: {
      customBodyRenderLite: renderManage,
    },
  });

  const options = {
    search: true,
    onSearchChange: handleSearchChange,
    selectableRows: "none",
    rowHover: false,
    print: false,
    elevation: 1,
    onTableChange: handleTableChange,
    jumpToPage: true,
    serverSide: true,
    pagination: false,
    count: totalMatches,
    filter: true,
    sort: true,
    customToolbar: () => (
      <IconButton
        name="new_instrument"
        onClick={() => {
          openNewDialog();
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <Paper className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title={hideTitle === true ? "" : "Instruments"}
              data={instruments || []}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
        <Dialog
          open={newDialogOpen}
          onClose={closeNewDialog}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle>New Instrument</DialogTitle>
          <DialogContent dividers>
            <NewInstrument onClose={closeNewDialog} />
          </DialogContent>
        </Dialog>
        <Dialog
          open={editDialogOpen && instrumentToEditDelete !== null}
          onClose={closeEditDialog}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle>Edit Instrument</DialogTitle>
          <DialogContent dividers>
            <ModifyInstrument
              instrumentID={instrumentToEditDelete}
              onClose={closeEditDialog}
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

InstrumentTable.propTypes = {
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,

  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired,
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  telescopeInfo: PropTypes.bool,
  deletePermission: PropTypes.bool.isRequired,
};

InstrumentTable.defaultProps = {
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
  hideTitle: false,
  telescopeInfo: true,
};

export default InstrumentTable;

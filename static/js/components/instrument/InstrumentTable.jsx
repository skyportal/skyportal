import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import * as instrumentActions from "../../ducks/instrument";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import InstrumentForm from "./InstrumentForm";
import Button from "../Button";

const InstrumentTable = ({
  title = "Instruments",
  instruments,
  telescopes,
  managePermission,
  sortingCallback = null,
  paginateCallback = null,
  totalMatches = 0,
  numPerPage = 10,
  telescopeInfo = true,
  fixedHeader = false,
}) => {
  const dispatch = useDispatch();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [instrumentToEditDelete, setInstrumentToEditDelete] = useState(null);

  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setInstrumentToEditDelete(null);
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

  const renderInstrumentName = (dataIndex) => {
    const instrument = instruments[dataIndex];
    return (
      <Link to={`/instrument/${instrument.id}`}>{instrument?.name || ""}</Link>
    );
  };

  const renderTelescopeNickname = (dataIndex) => {
    const telescope_id = instruments[dataIndex]?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];
    return (
      <Link to={`/telescope/${telescope_id}`}>{telescope?.nickname || ""}</Link>
    );
  };

  const renderTelescopeLat = (dataIndex) => {
    const telescope_id = instruments[dataIndex]?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];
    return telescope?.lat;
  };

  const renderTelescopeLon = (dataIndex) => {
    const telescope_id = instruments[dataIndex]?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];
    return telescope?.lon;
  };

  const renderFilters = (dataIndex) => {
    const filters = instruments[dataIndex]?.filters;
    return filters?.map((filter) => <div key={filter}>{filter}</div>);
  };

  const renderAPIClassnames = (dataIndex) => {
    const apiClassname = instruments[dataIndex]?.api_classname;
    const apiClassnameObsPlan = instruments[dataIndex]?.api_classname_obsplan;
    if (!apiClassname && !apiClassnameObsPlan) return null;

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "2px",
          alignItems: "start",
        }}
      >
        {apiClassname && (
          <Tooltip title="API for Follow-up Requests" placement="top">
            <Chip label={apiClassname} />
          </Tooltip>
        )}
        {apiClassnameObsPlan && (
          <Tooltip title={"API for Observation Plan"} placement="bottom">
            <Chip label={apiClassnameObsPlan} />
          </Tooltip>
        )}
      </div>
    );
  };

  const renderManage = (dataIndex) => {
    if (!managePermission) return null;

    const instrument = instruments[dataIndex];
    return (
      <div style={{ display: "flex" }}>
        <Button
          onClick={() => {
            setEditDialogOpen(true);
            setInstrumentToEditDelete(instrument.id);
          }}
        >
          <EditIcon />
        </Button>
        <Button
          onClick={() => {
            setDeleteDialogOpen(true);
            setInstrumentToEditDelete(instrument.id);
          }}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const handleSearchChange = (searchText) => {
    if (!paginateCallback) return;
    const data = { name: searchText };
    paginateCallback(1, rowsPerPage, {}, data);
  };

  const handleTableChange = (action, tableState) => {
    if (!paginateCallback || !sortingCallback) return;
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
        sortThirdClickReset: true,
      },
    },
    {
      name: "instrument_name",
      label: "Instrument Name",
      options: {
        filter: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrumentName,
        setCellProps: () => ({ style: { textAlign: "center" } }),
      },
    },
  ];
  if (telescopeInfo === true) {
    columns.push({
      name: "telescope_nickname",
      label: "Telescope Nickname",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescopeNickname,
        setCellProps: () => ({ style: { textAlign: "center" } }),
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
    name: "API_classnames",
    label: "API Classnames",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderAPIClassnames,
    },
  });
  columns.push({
    name: "band",
    label: "Band",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
    },
  });
  columns.push({
    name: "type",
    label: "Type",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
    },
  });
  columns.push({
    name: "region_summary",
    label: "FOV Region?",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
    },
  });
  columns.push({
    name: "number_of_fields",
    label: "Fields",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
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
    ...(fixedHeader
      ? { fixedHeader: true, tableBodyHeight: "calc(100vh - 148px)" }
      : {}),
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
      <IconButton name="new_instrument" onClick={() => setNewDialogOpen(true)}>
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <MUIDataTable
        title={title}
        data={instruments || []}
        options={options}
        columns={columns}
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
      <Dialog
        open={editDialogOpen && instrumentToEditDelete !== null}
        onClose={closeEditDialog}
        maxWidth="md"
      >
        <DialogTitle>
          Edit {instruments.find((i) => i.id === instrumentToEditDelete)?.name}{" "}
          instrument
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
    </div>
  );
};

InstrumentTable.propTypes = {
  title: PropTypes.string,
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,
  telescopes: PropTypes.arrayOf(PropTypes.any),
  sortingCallback: PropTypes.func,
  paginateCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  telescopeInfo: PropTypes.bool,
  managePermission: PropTypes.bool,
  fixedHeader: PropTypes.bool,
};

InstrumentTable.defaultProps = {
  title: "Instruments",
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
  paginateCallback: null,
  telescopeInfo: true,
  fixedHeader: false,
};

export default InstrumentTable;

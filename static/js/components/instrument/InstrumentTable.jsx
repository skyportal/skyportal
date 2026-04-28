import React, { useMemo, useState } from "react";
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
  managePermission = false,
  telescopeInfo = true,
  fixedHeader = false,
}) => {
  const dispatch = useDispatch();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [instrumentToManage, setInstrumentToManage] = useState(null);

  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setInstrumentToManage(null);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setInstrumentToManage(null);
  };

  const deleteInstrument = () => {
    dispatch(instrumentActions.deleteInstrument(instrumentToManage)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Instrument deleted"));
          closeDeleteDialog();
        }
      },
    );
  };

  // Enrich instruments with telescope info and combined API classnames for search/sort/filter in the table
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

  const renderInstrumentName = (dataIndex) => {
    const instrument = enrichedInstruments[dataIndex];
    return (
      <Link to={`/instrument/${instrument.id}`}>{instrument?.name || ""}</Link>
    );
  };

  const renderTelescopeNickname = (dataIndex) => {
    const instrument = enrichedInstruments[dataIndex];
    return (
      <Link to={`/telescope/${instrument?.telescope_id}`}>
        {instrument?.telescope_nickname || ""}
      </Link>
    );
  };

  const renderFilters = (dataIndex) => {
    const filters = enrichedInstruments[dataIndex]?.filters;
    return filters?.map((filter) => <div key={filter}>{filter}</div>);
  };

  const renderAPIClassnames = (dataIndex) => {
    const apiClassname = enrichedInstruments[dataIndex]?.api_classname;
    const apiClassnameObsPlan =
      enrichedInstruments[dataIndex]?.api_classname_obsplan;
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

    const instrument = enrichedInstruments[dataIndex];
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

  const columns = [
    {
      name: "id",
      label: "ID",
      options: { display: false },
    },
    {
      name: "name",
      label: "Name",
      options: {
        customBodyRenderLite: renderInstrumentName,
      },
    },
    ...(telescopeInfo
      ? [
          {
            name: "telescope_nickname",
            label: "Telescope",
            options: {
              customBodyRenderLite: renderTelescopeNickname,
            },
          },
          {
            name: "lat",
            label: "Latitude",
          },
          {
            name: "lon",
            label: "Longitude",
          },
        ]
      : []),
    {
      name: "filters",
      label: "Filters",
      options: {
        customBodyRenderLite: renderFilters,
      },
    },
    {
      name: "api_classnames",
      label: "API Classnames",
      options: {
        customBodyRenderLite: renderAPIClassnames,
      },
    },
    {
      name: "band",
      label: "Band",
    },
    {
      name: "type",
      label: "Type",
    },
    {
      name: "region_summary",
      label: "FOV Region?",
    },
    {
      name: "number_of_fields",
      label: "Fields",
    },
    {
      name: "manage",
      label: " ",
      options: {
        customBodyRenderLite: renderManage,
      },
    },
  ];

  const options = {
    ...(fixedHeader
      ? { fixedHeader: true, tableBodyHeight: "calc(100vh - 148px)" }
      : {}),
    search: true,
    selectableRows: "none",
    rowHover: false,
    print: false,
    elevation: 1,
    jumpToPage: true,
    pagination: false,
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
        data={enrichedInstruments}
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
    </div>
  );
};

InstrumentTable.propTypes = {
  title: PropTypes.string,
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,
  telescopes: PropTypes.arrayOf(PropTypes.any),
  telescopeInfo: PropTypes.bool,
  managePermission: PropTypes.bool,
  fixedHeader: PropTypes.bool,
};

export default InstrumentTable;

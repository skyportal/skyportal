import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MUIDataTable from "mui-datatables";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import {
  submitTelescope,
  editTelescope,
  deleteTelescope as deleteTelescopeAction,
} from "../../ducks/telescopes";
import { Link } from "react-router-dom";

const TelescopeTable = ({
  telescopes,
  managePermission = false,
  hideTitle = false,
}) => {
  const dispatch = useDispatch();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [telescopeToEdit, setTelescopeToEdit] = useState(null);
  const [telescopeToDelete, setTelescopeToDelete] = useState(null);
  const [formData, setFormData] = useState({});

  const cleanNulls = (data) =>
    Object.fromEntries(Object.entries(data).filter(([, v]) => v !== null));

  const deleteTelescope = () => {
    dispatch(deleteTelescopeAction(telescopeToDelete.id)).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Telescope deleted"));
        setTelescopeToDelete(null);
      }
    });
  };

  const closeDialog = () => {
    setNewDialogOpen(false);
    setTelescopeToEdit(null);
    setFormData({});
  };

  const handleSubmit = async () => {
    const action = telescopeToEdit
      ? editTelescope(formData)
      : submitTelescope(formData);
    const result = await dispatch(action);
    if (result.status === "success") closeDialog();
  };

  const uiSchema = {
    robotic: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
    fixed_location: {
      "ui:widget": "radio",
      "ui:labels": ["Yes", "No"],
    },
  };

  function validate(data, errors) {
    telescopes?.forEach((telescope) => {
      if (data.id !== telescope.id && data.name === telescope.name) {
        errors.name.addError("Telescope name matches another, please change.");
      }
    });
    if (data.fixed_location) {
      if (data.lon < -180 || data.lon > 180) {
        errors.lon.addError("Longitude must be between -180 and 180.");
      }
      if (data.lat < -90 || data.lat > 90) {
        errors.lat.addError("Latitude must be between -90 and 90.");
      }
      if (data.elevation < 0) {
        errors.elevation.addError("Elevation must be positive.");
      }
    }

    return errors;
  }

  const telescopeFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
      },
      nickname: {
        type: "string",
        title: "Nickname (e.g., P200)",
      },
      lat: {
        type: "number",
        title: "Latitude [deg]",
      },
      lon: {
        type: "number",
        title: "Longitude [deg]",
      },
      elevation: {
        type: "number",
        title: "Elevation [m]",
      },
      diameter: {
        type: "number",
        title: "Diameter [m]",
      },
      skycam_link: {
        type: "string",
        title: "Sky camera URL",
      },
      weather_link: {
        type: "string",
        title: "Preferred weather site URL",
      },
      robotic: {
        type: "boolean",
        title: "Is this telescope robotic?",
      },
      fixed_location: {
        type: "boolean",
        title: "Does this telescope have a fixed location (lon, lat, elev)?",
      },
    },
    required: [
      "name",
      "nickname",
      "diameter",
      "robotic",
      "fixed_location",
    ].concat(formData.fixed_location ? ["lon", "lat", "elevation"] : []),
  };

  const renderManage = (dataIndex) => {
    if (!managePermission) return null;

    const telescope = telescopes[dataIndex];
    return (
      <Box sx={{ display: "flex" }}>
        <Button
          onClick={() => {
            setTelescopeToEdit(telescope);
            setFormData(cleanNulls(telescope));
          }}
        >
          <EditIcon />
        </Button>
        <Button onClick={() => setTelescopeToDelete(telescope)} color="error">
          <DeleteIcon />
        </Button>
      </Box>
    );
  };

  const columns = [
    {
      name: "name",
      label: "Name",
      options: {
        customBodyRenderLite: (dataIndex) => (
          <Link to={`/telescope/${telescopes[dataIndex].id}`}>
            {telescopes[dataIndex].name}
          </Link>
        ),
      },
    },
    {
      name: "nickname",
      label: "Nickname",
    },
    {
      name: "lat",
      label: "Latitude",
      options: {
        customBodyRender: (value) => value?.toFixed(4),
      },
    },
    {
      name: "lon",
      label: "Longitude",
      options: {
        customBodyRender: (value) => value?.toFixed(4),
      },
    },
    {
      name: "elevation",
      label: "Elevation",
      options: {
        customBodyRender: (value) => value?.toFixed(1),
      },
    },
    {
      name: "diameter",
      label: "Diameter",
      options: {
        customBodyRender: (value) => value?.toFixed(1),
      },
    },
    {
      name: "robotic",
      label: "Robotic",
      options: {
        customBodyRender: (value) =>
          value ? (
            <Chip label="Yes" color="primary" size="small" />
          ) : (
            <Chip label="No" size="small" />
          ),
      },
    },
    {
      name: "fixed_location",
      label: "Fixed Location",
      options: {
        customBodyRender: (value) =>
          value ? (
            <Chip label="Yes" color="primary" size="small" />
          ) : (
            <Chip label="No" size="small" />
          ),
      },
    },
    {
      name: "skycam_link",
      label: "Skycam",
      options: {
        customBodyRender: (value) =>
          value && (
            <a href={value} target="_blank" rel="noopener noreferrer">
              View
            </a>
          ),
      },
    },
    {
      name: "manage",
      label: "",
      options: {
        customBodyRenderLite: renderManage,
        sort: false,
        filter: false,
      },
    },
  ];

  const options = {
    fixedHeader: true,
    tableBodyHeight: "calc(100vh - 148px)",
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
      <IconButton name="new_telescope" onClick={() => setNewDialogOpen(true)}>
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <MUIDataTable
        title={!hideTitle ? "Telescopes" : ""}
        data={telescopes || []}
        options={options}
        columns={columns}
      />
      <Dialog
        open={newDialogOpen || telescopeToEdit !== null}
        onClose={closeDialog}
        maxWidth="md"
      >
        <DialogTitle>
          {telescopeToEdit
            ? `Edit Telescope: ${telescopeToEdit.name}`
            : "New Telescope"}
        </DialogTitle>
        <DialogContent dividers>
          <Form
            schema={telescopeFormSchema}
            formData={formData}
            onChange={(e) => setFormData(e.formData)}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit}
            customValidate={validate}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteTelescope}
        dialogOpen={telescopeToDelete !== null}
        closeDialog={() => setTelescopeToDelete(null)}
        resourceName="telescope"
      />
    </div>
  );
};

TelescopeTable.propTypes = {
  telescopes: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      nickname: PropTypes.string,
      lat: PropTypes.number,
      lon: PropTypes.number,
      elevation: PropTypes.number,
      diameter: PropTypes.number,
      robotic: PropTypes.bool,
      fixed_location: PropTypes.bool,
      skycam_link: PropTypes.string,
    }),
  ).isRequired,
  hideTitle: PropTypes.bool,
  managePermission: PropTypes.bool,
};

export default TelescopeTable;

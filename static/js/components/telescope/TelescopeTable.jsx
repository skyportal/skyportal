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

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import * as telescopesActions from "../../ducks/telescopes";
import Chip from "@mui/material/Chip";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { fetchTelescopes, submitTelescope } from "../../ducks/telescopes";

const useStyles = makeStyles(() => ({
  telescopeManage: {
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
      MUIDataTableToolbar: {
        styleOverrides: {
          left: {
            paddingLeft: "0.5rem",
          },
        },
      },
    },
  });

const TelescopeTable = ({
  telescopes,
  deletePermission,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [telescopeToEditDelete, setTelescopeToEditDelete] = useState(null);

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setTelescopeToEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setTelescopeToEditDelete(null);
  };

  const deleteTelescope = () => {
    dispatch(telescopesActions.deleteTelescope(telescopeToEditDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Telescope deleted"));
          closeDeleteDialog();
        }
      },
    );
  };

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(submitTelescope(formData));
    if (result.status === "success") {
      dispatch(showNotification("Telescope saved"));
      dispatch(fetchTelescopes());
      setNewDialogOpen(false);
    }
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

  function validate(formData, errors) {
    telescopes?.forEach((telescope) => {
      if (formData.name === telescope.name) {
        errors.name.addError("Telescope name matches another, please change.");
      }
    });
    if (formData.fixed_location === true) {
      if (formData.lon === undefined) {
        errors.lon.addError(
          "Longitude must be specified if telescope is fixed.",
        );
      } else if (formData.lon < -180 || formData.lon > 180) {
        errors.lon.addError("Longitude must be between -180 and 180.");
      }
      if (formData.lat === undefined) {
        errors.lat.addError(
          "Latitude must be specified if telescope is fixed.",
        );
      } else if (formData.lat < -90 || formData.lat > 90) {
        errors.lat.addError("Latitude must be between -90 and 90.");
      }
      if (formData.elevation === undefined) {
        errors.elevation.addError(
          "Elevation must be specified if telescope is fixed.",
        );
      } else if (formData.elevation < 0) {
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
    required: ["name", "nickname", "diameter", "robotic", "fixed_location"],
  };

  const renderManage = (dataIndex) => {
    if (!deletePermission) {
      return null;
    }
    const telescope = telescopes[dataIndex];
    return (
      <div className={classes.telescopeManage}>
        <Button
          key={`delete_${telescope.id}`}
          id={`delete_button_${telescope.id}`}
          onClick={() => openDeleteDialog(telescope.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "name",
      label: "Name",
    },
    {
      name: "nickname",
      label: "Nickname",
    },
    {
      name: "lat",
      label: "Latitude",
      options: {
        customBodyRender: (value) => value?.toFixed(4) ?? "—",
      },
    },
    {
      name: "lon",
      label: "Longitude",
      options: {
        customBodyRender: (value) => value?.toFixed(4) ?? "—",
      },
    },
    {
      name: "elevation",
      label: "Elevation",
      options: {
        customBodyRender: (value) => value?.toFixed(1) ?? "—",
      },
    },
    {
      name: "diameter",
      label: "Diameter",
      options: {
        customBodyRender: (value) => value?.toFixed(1) ?? "—",
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
          value ? (
            <a href={value} target="_blank" rel="noopener noreferrer">
              View
            </a>
          ) : (
            "—"
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
      <IconButton
        name="new_telescope"
        onClick={() => {
          setNewDialogOpen(true);
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <Paper>
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable
            title={hideTitle === true ? "" : "Telescopes"}
            data={telescopes || []}
            options={options}
            columns={columns}
          />
        </ThemeProvider>
      </StyledEngineProvider>
      <Dialog
        open={newDialogOpen}
        onClose={() => setNewDialogOpen(false)}
        maxWidth="md"
      >
        <DialogTitle>New Telescope</DialogTitle>
        <DialogContent dividers>
          <Form
            schema={telescopeFormSchema}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit}
            customValidate={validate}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteTelescope}
        dialogOpen={deleteDialogOpen}
        closeDialog={() => setDeleteDialogOpen(false)}
        resourceName="telescope"
      />
    </Paper>
  );
};

TelescopeTable.propTypes = {
  telescopes: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
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
  deletePermission: PropTypes.bool,
};

TelescopeTable.defaultProps = {
  hideTitle: false,
  deletePermission: false,
};

export default TelescopeTable;

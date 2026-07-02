import { useState, useMemo } from "react";
import Paper from "@mui/material/Paper";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Chip from "@mui/material/Chip";

import { showNotification } from "baselayer/components/Notifications";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import {
  useDeleteTelescopeMutation,
  useSubmitTelescopeMutation,
} from "../../ducks/telescopes";
import { useAppDispatch } from "../../types/hooks";

const useStyles = makeStyles()(() => ({
  telescopeManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

interface TelescopeTableProps {
  telescopes: any[];
  deletePermission?: boolean;
  hideTitle?: boolean;
}

const TelescopeTable = ({
  telescopes,
  deletePermission = false,
  hideTitle = false,
}: TelescopeTableProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [deleteTelescopeMutation] = useDeleteTelescopeMutation();
  const [submitTelescopeMutation] = useSubmitTelescopeMutation();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [telescopeToEditDelete, setTelescopeToEditDelete] = useState<any>(null);

  const openDeleteDialog = (id: any) => {
    setDeleteDialogOpen(true);
    setTelescopeToEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setTelescopeToEditDelete(null);
  };

  const deleteTelescope = async () => {
    try {
      await deleteTelescopeMutation(telescopeToEditDelete).unwrap();
      dispatch(showNotification("Telescope deleted"));
      closeDeleteDialog();
    } catch {
      // error notification handled by the API base query
    }
  };

  const handleSubmit = async ({ formData }: { formData: any }) => {
    try {
      await submitTelescopeMutation(formData).unwrap();
      dispatch(showNotification("Telescope saved"));
      setNewDialogOpen(false);
    } catch {
      // error notification handled by the API base query
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

  function validate(formData: any, errors: any) {
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

  const renderManage = (params: any) => {
    if (!deletePermission) {
      return null;
    }
    const telescope = params.row;
    return (
      <div className={classes.telescopeManage}>
        <Button
          id={`delete_button_${telescope.id}`}
          onClick={() => openDeleteDialog(telescope.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const renderBool = (params: any) =>
    params.value ? (
      <Chip label="Yes" color="primary" size="small" />
    ) : (
      <Chip label="No" size="small" />
    );

  const columns: any[] = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 120 },
    { field: "nickname", headerName: "Nickname", flex: 1, minWidth: 100 },
    {
      field: "lat",
      headerName: "Latitude",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(4) ?? "—",
    },
    {
      field: "lon",
      headerName: "Longitude",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(4) ?? "—",
    },
    {
      field: "elevation",
      headerName: "Elevation",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(1) ?? "—",
    },
    {
      field: "diameter",
      headerName: "Diameter",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(1) ?? "—",
    },
    {
      field: "robotic",
      headerName: "Robotic",
      width: 100,
      renderCell: renderBool,
    },
    {
      field: "fixed_location",
      headerName: "Fixed Location",
      width: 130,
      renderCell: renderBool,
    },
    {
      field: "skycam_link",
      headerName: "Skycam",
      width: 100,
      sortable: false,
      renderCell: (params: any) =>
        params.value ? (
          <a href={params.value} target="_blank" rel="noopener noreferrer">
            View
          </a>
        ) : (
          "—"
        ),
    },
    {
      field: "manage",
      headerName: "",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ];

  // Memoized (like SourceTable/GalaxyTable) so the toolbar slot keeps a stable
  // identity; an inline slot remounts each render and loops the grid.
  const CustomToolbar = useMemo(
    () =>
      function TelescopeTableToolbar() {
        return (
          <DataGridToolbar>
            <IconButton
              name="new_telescope"
              onClick={() => setNewDialogOpen(true)}
            >
              <AddIcon />
            </IconButton>
          </DataGridToolbar>
        );
      },
    [],
  );

  return (
    <Paper>
      {hideTitle !== true && (
        <Typography variant="h6" sx={{ p: 1 }}>
          Telescopes
        </Typography>
      )}
      <Box sx={{ width: "100%", height: "calc(100vh - 148px)" }}>
        <StyledDataGrid
          rows={telescopes || []}
          columns={columns}
          getRowId={(row: any) => row.id}
          hideFooter
          initialState={{
            pagination: { paginationModel: { pageSize: 100 } },
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
        <DialogTitle>New Telescope</DialogTitle>
        <DialogContent dividers>
          <Form
            schema={telescopeFormSchema as any}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit as any}
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

export default TelescopeTable;

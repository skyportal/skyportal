import { useState, useMemo } from "react";
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
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import {
  useDeleteTelescopeMutation,
  useSubmitTelescopeMutation,
  useUpdateTelescopeMutation,
} from "../../ducks/telescopes";
import { useAppDispatch } from "../../types/hooks";
import { useIsReadOnly } from "../../ducks/profile";

import EditIcon from "@mui/icons-material/Edit";
import Box from "@mui/material/Box";

interface TelescopeTableProps {
  telescopes: any[];
  managePermission?: boolean;
  hideTitle?: boolean;
}

const TelescopeTable = ({
  telescopes,
  managePermission = false,
  hideTitle = false,
}: TelescopeTableProps) => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [deleteTelescopeMutation] = useDeleteTelescopeMutation();
  const [submitTelescopeMutation] = useSubmitTelescopeMutation();
  const [updateTelescopeMutation] = useUpdateTelescopeMutation();

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [telescopeToEdit, setTelescopeToEdit] = useState<any>(null);
  const [telescopeToDelete, setTelescopeToDelete] = useState<any>(null);
  const [formData, setFormData] = useState<any>({});

  const cleanNulls = (data: any) =>
    Object.fromEntries(Object.entries(data).filter(([, v]) => v !== null));

  const deleteTelescope = async () => {
    try {
      await deleteTelescopeMutation(telescopeToDelete.id).unwrap();
      dispatch(showNotification("Telescope deleted"));
      setTelescopeToDelete(null);
    } catch {
      // error notification handled by the API base query
    }
  };

  const closeDialog = () => {
    setNewDialogOpen(false);
    setTelescopeToEdit(null);
    setFormData({});
  };

  const handleSubmit = async () => {
    try {
      if (telescopeToEdit) {
        await updateTelescopeMutation({
          id: telescopeToEdit.id,
          data: formData,
        }).unwrap();
      } else {
        await submitTelescopeMutation(formData).unwrap();
      }
      dispatch(showNotification("Telescope saved"));
      closeDialog();
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

  function validate(data: any, errors: any) {
    telescopes.forEach((telescope) => {
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

  const renderManage = (params: any) => {
    if (!managePermission) return null;
    const telescope = params.row;
    return (
      <Box sx={{ display: "flex" }}>
        <IconButton
          onClick={() => {
            setTelescopeToEdit(telescope);
            setFormData(cleanNulls(telescope));
          }}
        >
          <EditIcon />
        </IconButton>
        <IconButton
          color="error"
          onClick={() => setTelescopeToDelete(telescope)}
        >
          <DeleteIcon />
        </IconButton>
      </Box>
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
      valueFormatter: (value: any) => value?.toFixed(4),
    },
    {
      field: "lon",
      headerName: "Longitude",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(4),
    },
    {
      field: "elevation",
      headerName: "Elevation",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(1),
    },
    {
      field: "diameter",
      headerName: "Diameter",
      flex: 1,
      minWidth: 100,
      valueFormatter: (value: any) => value?.toFixed(1),
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
        ) : null,
    },
    managePermission && {
      field: "manage",
      headerName: "",
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ].filter(Boolean);

  // Memoized (like SourceTable/GalaxyTable) so the toolbar slot keeps a stable
  // identity; an inline slot remounts each render and loops the grid.
  const CustomToolbar = useMemo(
    () =>
      function TelescopeTableToolbar() {
        return (
          <DataGridToolbar title={hideTitle ? "" : "Telescopes"}>
            {!isReadOnly && (
              <IconButton
                name="new_telescope"
                onClick={() => setNewDialogOpen(true)}
              >
                <AddIcon />
              </IconButton>
            )}
          </DataGridToolbar>
        );
      },
    [isReadOnly],
  );

  return (
    <Box sx={{ width: "100%", height: "calc(100vh - 5rem)" }}>
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
            schema={telescopeFormSchema as any}
            formData={formData}
            onChange={(e) => setFormData(e.formData)}
            validator={validator}
            uiSchema={uiSchema}
            onSubmit={handleSubmit as any}
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
    </Box>
  );
};

export default TelescopeTable;

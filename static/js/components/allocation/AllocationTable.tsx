import { useState } from "react";
import { useTheme } from "@mui/material/styles";
import { Link } from "react-router-dom";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import { useDeleteAllocationMutation } from "../../ducks/allocation";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import AllocationForm from "./AllocationForm";
import { userLabel } from "../../utils/format";
import { useIsReadOnly } from "../../ducks/profile";

export const isSomeActiveRangeOrNoRange = (
  ranges: any,
  date: Date = new Date(),
) => {
  return (
    !ranges?.length || ranges.some((range: any) => rangeIsActive(range, date))
  );
};

export const rangeIsActive = (range: any, date: Date = new Date()) =>
  range.start_date <= date.toISOString() &&
  range.end_date >= date.toISOString();

interface AllocationTableProps {
  title?: string;
  groups?: any[];
  allocations: any[];
  telescopes?: any[];
  instruments: any[];
  managePermission?: boolean;
  telescopeInfo?: boolean;
  fixedHeader?: boolean;
}

const AllocationTable = ({
  title = "Allocations",
  groups = [],
  allocations,
  telescopes,
  instruments,
  managePermission = false,
  telescopeInfo = true,
  fixedHeader = false,
}: AllocationTableProps) => {
  const theme = useTheme();

  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const [newAllocationDialog, setNewAllocationDialog] = useState(false);
  const [allocationToEdit, setAllocationToEdit] = useState<any>(null);
  const [allocationToDelete, setAllocationToDelete] = useState<any>(null);

  const [deleteAllocationMutation] = useDeleteAllocationMutation();

  const deleteAllocation = async () => {
    try {
      await deleteAllocationMutation(allocationToDelete).unwrap();
      dispatch(showNotification("Allocation deleted"));
      setAllocationToDelete(null);
    } catch {
      // error notification handled by the baseQuery
    }
  };

  const getInstrument = (allocation: any) =>
    instruments?.filter((i) => i.id === allocation.instrument_id)[0];

  const renderInstrumentName = (params: any) => {
    const allocation = params.row;
    const instrument = getInstrument(allocation);
    return (
      <Link to={`/instrument/${allocation.instrument_id}`}>
        {instrument?.name || ""}
      </Link>
    );
  };

  const renderTelescopeNickname = (params: any) => {
    const allocation = params.row;
    const instrument = getInstrument(allocation);
    const telescope = telescopes?.filter(
      (t) => t.id === instrument?.telescope_id,
    )[0];
    return (
      <Link to={`/telescope/${telescope?.id}`}>
        {telescope?.nickname || ""}
      </Link>
    );
  };

  const getGroupName = (params: any) => {
    const allocation = params.row;
    const group = groups?.find((g) => g.id === allocation.group_id);
    if (!group?.name) return null;
    return <Chip label={group?.name} />;
  };

  const getShareGroups = (params: any) => {
    const allocation = params.row;
    if (!allocation?.default_share_group_ids?.length) return null;
    return allocation.default_share_group_ids.map((share_group_id: any) => (
      <Chip
        key={share_group_id}
        label={groups?.find((g) => g.id === share_group_id)?.name || ""}
      />
    ));
  };

  const getAllocationUsers = (params: any) => {
    const allocation = params.row;
    if (!allocation?.allocation_users?.length) return null;
    return allocation.allocation_users.map((user: any) => (
      <Chip key={user.id} label={userLabel(user, true, true, true)} />
    ));
  };

  const renderValidityRanges = (params: any) => {
    const validity_ranges = (params.row?.validity_ranges || []).filter(
      (range: any) => range.end_date >= new Date().toISOString(),
    );

    const formatOptions: any = {
      hour12: false,
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    };
    return (
      <Tooltip
        title={
          validity_ranges?.map((range: any) => (
            <Typography
              key={`${range.start_date}`}
              variant="body1"
              sx={{ color: rangeIsActive(range) ? "lightgreen" : "white" }}
            >
              {new Date(range.start_date).toLocaleString(
                "en-US",
                formatOptions,
              )}{" "}
              -{" "}
              {new Date(range.end_date).toLocaleString("en-US", formatOptions)}
            </Typography>
          )) || (
            <Typography variant="body2" sx={{ textAlign: "center" }}>
              No validity ranges defined for this allocation.
            </Typography>
          )
        }
      >
        {isSomeActiveRangeOrNoRange(validity_ranges) ? (
          <Chip
            label={!validity_ranges.length ? "Always Active" : "Active"}
            color="success"
          />
        ) : (
          <Chip
            label="Inactive"
            sx={{ color: theme.palette.action.disabled }}
          />
        )}
      </Tooltip>
    );
  };

  const renderManage = (params: any) => {
    if (!managePermission) return null;
    const allocation = params.row;
    return (
      <Box style={{ display: "flex" }}>
        <IconButton onClick={() => setAllocationToEdit(allocation.id)}>
          <EditIcon />
        </IconButton>
        <IconButton
          color="error"
          onClick={() => setAllocationToDelete(allocation.id)}
        >
          <DeleteIcon />
        </IconButton>
      </Box>
    );
  };

  const columns: any[] = [
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
      valueGetter: (_value: any, row: any) => row.id ?? "",
    },
    {
      field: "instrument_name",
      headerName: "Instrument Name",
      flex: 1,
      minWidth: 150,
      filterable: false,
      valueGetter: (_value: any, row: any) => getInstrument(row)?.name || "",
      renderCell: renderInstrumentName,
    },
    telescopeInfo && {
      field: "telescope_name",
      headerName: "Telescope Nickname",
      flex: 1,
      minWidth: 150,
      filterable: false,
      valueGetter: (_value: any, row: any) => {
        const instrument = getInstrument(row);
        const telescope = telescopes?.filter(
          (t) => t.id === instrument?.telescope_id,
        )[0];
        return telescope ? telescope.nickname : "";
      },
      renderCell: renderTelescopeNickname,
    },
    {
      field: "PI",
      headerName: "PI",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.pi || "",
    },
    {
      field: "Group",
      headerName: "Group",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: getGroupName,
    },
    {
      field: "default_share_group",
      headerName: "Default Share Groups",
      flex: 1,
      minWidth: 160,
      filterable: false,
      renderCell: getShareGroups,
    },
    {
      field: "admins",
      headerName: "Admins",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: getAllocationUsers,
    },
    {
      field: "types",
      headerName: "Types",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (_value: any, row: any) =>
        row.types ? row.types.join(", ") : "",
    },
    {
      field: "validity_ranges",
      headerName: "Validity Ranges",
      flex: 1,
      minWidth: 140,
      sortable: false,
      filterable: false,
      renderCell: renderValidityRanges,
    },
    managePermission && {
      field: "manage",
      headerName: " ",
      width: 120,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ].filter(Boolean);

  const CustomToolbar = () => (
    <DataGridToolbar title={title}>
      {!isReadOnly && (
        <IconButton
          name="new_allocation"
          size="small"
          onClick={() => setNewAllocationDialog(true)}
        >
          <AddIcon />
        </IconButton>
      )}
    </DataGridToolbar>
  );

  return (
    <Box
      sx={{
        height: fixedHeader ? "calc(100vh - 201px)" : "auto",
        width: "100%",
      }}
    >
      <StyledDataGrid
        autoHeight={!fixedHeader}
        rows={allocations || []}
        columns={columns}
        getRowId={(row: any) => row.id}
        hideFooter
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Dialog
        open={newAllocationDialog}
        onClose={() => setNewAllocationDialog(false)}
        maxWidth="md"
      >
        <DialogTitle>New Allocation</DialogTitle>
        <DialogContent dividers>
          <AllocationForm onClose={() => setNewAllocationDialog(false)} />
        </DialogContent>
      </Dialog>
      <Dialog
        open={allocationToEdit !== null}
        onClose={() => setAllocationToEdit(null)}
        maxWidth="md"
      >
        <DialogTitle>Edit Allocation</DialogTitle>
        <DialogContent dividers>
          <AllocationForm
            onClose={() => setAllocationToEdit(null)}
            allocationId={allocationToEdit}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteAllocation}
        dialogOpen={allocationToDelete !== null}
        closeDialog={() => setAllocationToDelete(null)}
        resourceName="allocation"
      />
    </Box>
  );
};

export default AllocationTable;

import React, { useState } from "react";
import Paper from "@mui/material/Paper";
import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
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
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarQuickFilter,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import StyledDataGrid from "../StyledDataGrid";
import * as allocationActions from "../../ducks/allocation";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import AllocationForm from "./AllocationForm";
import { userLabel } from "../../utils/format";

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

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map fall through to the field itself.
const SERVER_SORT_FIELD: Record<string, string> = {
  id: "id",
  instrument_name: "instrument_name",
  telescope_name: "telescope_name",
  PI: "PI",
  Group: "Group",
};

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  allocationManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

interface AllocationTableProps {
  title?: string;
  groups?: any[];
  allocations: any[];
  telescopes?: any[];
  instruments: any[];
  sortingCallback?: ((...a: any[]) => void) | null;
  paginateCallback?: ((...a: any[]) => void) | null;
  totalMatches?: number;
  numPerPage?: number;
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
  sortingCallback = null,
  paginateCallback = null,
  totalMatches = 0,
  numPerPage = 10,
  managePermission = false,
  telescopeInfo = true,
  fixedHeader = false,
}: AllocationTableProps) => {
  const { classes } = useStyles();
  const theme = useTheme();

  const dispatch = useAppDispatch();

  const [rowsPerPage] = useState(numPerPage);
  const [sortModel, setSortModel] = useState<any[]>([]);

  const [newAllocationDialog, setNewAllocationDialog] = useState(false);
  const [allocationToEdit, setAllocationToEdit] = useState<any>(null);
  const [allocationToDelete, setAllocationToDelete] = useState<any>(null);

  const deleteAllocation = () => {
    dispatch(allocationActions.deleteAllocation(allocationToDelete)).then(
      (result: any) => {
        if (result.status === "success") {
          dispatch(showNotification("Allocation deleted"));
          setAllocationToDelete(null);
        }
      },
    );
  };

  const getInstrument = (allocation: any) =>
    instruments?.filter((i) => i.id === allocation.instrument_id)[0];

  const renderInstrumentName = (params: any) => {
    const allocation = params.row;
    const instrument = getInstrument(allocation);
    return (
      <Link to={`/allocation/${allocation.id}`} role="link">
        {instrument ? instrument.name : ""}
      </Link>
    );
  };

  const renderTelescopeName = (params: any) => {
    const allocation = params.row;
    const instrument = getInstrument(allocation);
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];
    return (
      <Link to={`/allocation/${allocation.id}`} role="link">
        {telescope ? telescope.nickname : ""}
      </Link>
    );
  };

  const getGroupName = (allocation: any) => {
    const group = groups?.filter((g) => g.id === allocation.group_id)[0];
    return group ? group.name : "";
  };

  const getShareGroups = (allocation: any) => {
    const share_groups: any[] = [];
    if (allocation.default_share_group_ids?.length > 0) {
      allocation.default_share_group_ids.forEach((share_group_id: any) => {
        share_groups.push(
          groups?.filter((g) => g.id === share_group_id)[0].name,
        );
      });
    }
    return share_groups.length > 0 ? share_groups.join("\n") : "";
  };

  const getAllocationUsers = (allocation: any) => {
    const allocation_users: any[] = [];
    if (allocation.allocation_users?.length > 0) {
      allocation.allocation_users.forEach((user: any) => {
        allocation_users.push(userLabel(user, true, true, true));
      });
    }
    return allocation_users.length > 0 ? allocation_users.join("\n") : "";
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
          <>
            {validity_ranges.length ? (
              validity_ranges.map((range: any) => (
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
                  {new Date(range.end_date).toLocaleString(
                    "en-US",
                    formatOptions,
                  )}
                </Typography>
              ))
            ) : (
              <Typography variant="body2" sx={{ textAlign: "center" }}>
                No validity ranges defined for this allocation.
              </Typography>
            )}
          </>
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
      <div className={classes.allocationManage}>
        <IconButton
          id={`edit_button_${allocation.id}`}
          onClick={() => setAllocationToEdit(allocation.id)}
        >
          <EditIcon />
        </IconButton>
        <IconButton
          id={`delete_button_${allocation.id}`}
          onClick={() => setAllocationToDelete(allocation.id)}
        >
          <DeleteIcon />
        </IconButton>
      </div>
    );
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    if (!paginateCallback || !sortingCallback) return;
    if (!model.length) {
      paginateCallback(1, rowsPerPage, {});
      return;
    }
    const { field, sort } = model[0];
    sortingCallback({
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const columns: any[] = [
    {
      field: "id",
      headerName: "ID",
      flex: 1,
      minWidth: 80,
      valueGetter: (value: any, row: any) => row.id ?? "",
    },
    {
      field: "instrument_name",
      headerName: "Instrument Name",
      flex: 1,
      minWidth: 150,
      filterable: false,
      valueGetter: (value: any, row: any) => getInstrument(row)?.name || "",
      renderCell: renderInstrumentName,
    },
    telescopeInfo && {
      field: "telescope_name",
      headerName: "Telescope Name",
      flex: 1,
      minWidth: 150,
      filterable: false,
      valueGetter: (value: any, row: any) => {
        const instrument = getInstrument(row);
        const telescope = telescopes?.filter(
          (t) => t.id === instrument?.telescope_id,
        )[0];
        return telescope ? telescope.nickname : "";
      },
      renderCell: renderTelescopeName,
    },
    {
      field: "PI",
      headerName: "PI",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (value: any, row: any) => row.pi || "",
    },
    {
      field: "Group",
      headerName: "Group",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (value: any, row: any) => getGroupName(row),
    },
    {
      field: "default_share_group",
      headerName: "Default Share Groups",
      flex: 1,
      minWidth: 160,
      filterable: false,
      valueGetter: (value: any, row: any) => getShareGroups(row),
    },
    {
      field: "admins",
      headerName: "Admins",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (value: any, row: any) => getAllocationUsers(row),
    },
    {
      field: "types",
      headerName: "Types",
      flex: 1,
      minWidth: 120,
      filterable: false,
      valueGetter: (value: any, row: any) =>
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
      width: 110,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ].filter(Boolean);

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <IconButton
        name="new_allocation"
        size="small"
        onClick={() => setNewAllocationDialog(true)}
      >
        <AddIcon />
      </IconButton>
      <GridToolbarQuickFilter />
    </GridToolbarContainer>
  );

  // mui-datatables ran with pagination:false (show-all). DataGrid mirrors that
  // by hiding the footer and rendering every row; sorting stays server-side so
  // the page's sortingCallback continues to drive the fetch.
  const serverSide = paginateCallback !== null && sortingCallback !== null;

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" style={{ padding: "0.5rem" }}>
          {title}
        </Typography>
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
            rowCount={totalMatches}
            sortingMode={serverSide ? "server" : "client"}
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            hideFooter
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
      </Paper>
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
    </div>
  );
};

export default AllocationTable;

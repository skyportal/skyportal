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
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import * as allocationActions from "../../ducks/allocation";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import AllocationForm from "./AllocationForm";
import { userLabel } from "../../utils/format";

export const isSomeActiveRangeOrNoRange = (ranges, date = new Date()) => {
  return !ranges?.length || ranges.some((range) => rangeIsActive(range, date));
};

export const rangeIsActive = (range, date = new Date()) =>
  range.start_date <= date.toISOString() &&
  range.end_date >= date.toISOString();

const useStyles = makeStyles(() => ({
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
  deletePermission = false,
  telescopeInfo = true,
  fixedHeader = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  const dispatch = useDispatch();

  const [setRowsPerPage] = useState(numPerPage);

  const [newAllocationDialog, setNewAllocationDialog] = useState(false);
  const [allocationToEdit, setAllocationToEdit] = useState(null);
  const [allocationToDelete, setAllocationToDelete] = useState(null);

  const deleteAllocation = () => {
    dispatch(allocationActions.deleteAllocation(allocationToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Allocation deleted"));
          setAllocationToDelete(null);
        }
      },
    );
  };

  const renderAllocationID = (dataIndex) => {
    const allocation = allocations[dataIndex];

    return <div>{allocation ? allocation.id : ""}</div>;
  };

  const renderInstrumentName = (dataIndex) => {
    const allocation = allocations[dataIndex];
    const { instrument_id } = allocation;
    const instrument = instruments?.filter((i) => i.id === instrument_id)[0];

    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {instrument ? instrument.name : ""}
        </Link>
      </div>
    );
  };

  const renderTelescopeName = (dataIndex) => {
    const allocation = allocations[dataIndex];

    const { instrument_id } = allocation;
    const instrument = instruments?.filter((i) => i.id === instrument_id)[0];

    const telescope_id = instrument?.telescope_id;
    const telescope = telescopes?.filter((t) => t.id === telescope_id)[0];

    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {telescope ? telescope.nickname : ""}
        </Link>
      </div>
    );
  };

  const renderGroup = (dataIndex) => {
    const allocation = allocations[dataIndex];
    const group = groups?.filter((g) => g.id === allocation.group_id)[0];

    return <div>{group ? group.name : ""}</div>;
  };

  const renderShareGroups = (dataIndex) => {
    const allocation = allocations[dataIndex];

    const share_groups = [];
    if (allocation.default_share_group_ids?.length > 0) {
      allocation.default_share_group_ids.forEach((share_group_id) => {
        share_groups.push(
          groups?.filter((g) => g.id === share_group_id)[0].name,
        );
      });
    }

    return <div>{share_groups.length > 0 ? share_groups.join("\n") : ""}</div>;
  };

  const renderAllocationUsers = (dataIndex) => {
    const allocation = allocations[dataIndex];

    const allocation_users = [];
    if (allocation.allocation_users?.length > 0) {
      allocation.allocation_users.forEach((user) => {
        allocation_users.push(userLabel(user, true, true, true));
      });
    }

    return (
      <div>
        {allocation_users.length > 0 ? allocation_users.join("\n") : ""}
      </div>
    );
  };

  const renderValidityRanges = (dataIndex) => {
    const validity_ranges = (
      allocations[dataIndex]?.validity_ranges || []
    ).filter((range) => range.end_date >= new Date().toISOString());

    const formatOptions = {
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
              validity_ranges.map((range) => (
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

  const renderPI = (dataIndex) => {
    const allocation = allocations[dataIndex];

    return <div>{allocation ? allocation.pi : ""}</div>;
  };

  const renderTypes = (dataIndex) => {
    const allocation = allocations[dataIndex];
    return <div>{allocation ? allocation.types.join(", ") : ""}</div>;
  };

  const renderManage = (dataIndex) => {
    if (!deletePermission) {
      return null;
    }
    const allocation = allocations[dataIndex];
    return (
      <div className={classes.allocationManage}>
        <IconButton
          key={`edit_${allocation.id}`}
          id={`edit_button_${allocation.id}`}
          onClick={() => setAllocationToEdit(allocation.id)}
          disabled={!deletePermission}
        >
          <EditIcon />
        </IconButton>
        <IconButton
          key={`delete_${allocation.id}`}
          id={`delete_button_${allocation.id}`}
          onClick={() => setAllocationToDelete(allocation.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </IconButton>
      </div>
    );
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
        customBodyRenderLite: renderAllocationID,
      },
    },
    {
      name: "instrument_name",
      label: "Instrument Name",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrumentName,
      },
    },
    telescopeInfo && {
      name: "telescope_name",
      label: "Telescope Name",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTelescopeName,
      },
    },
    {
      name: "PI",
      label: "PI",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderPI,
      },
    },
    {
      name: "Group",
      label: "Group",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderGroup,
      },
    },
    {
      name: "default_share_group",
      label: "Default Share Groups",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderShareGroups,
      },
    },
    {
      name: "admins",
      label: "Admins",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderAllocationUsers,
      },
    },
    {
      name: "types",
      label: "Types",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderTypes,
      },
    },
    {
      name: "validity_ranges",
      label: "Validity Ranges",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderValidityRanges,
      },
    },
    deletePermission && {
      name: "manage",
      label: " ",
      options: {
        customBodyRenderLite: renderManage,
      },
    },
  ].filter(Boolean);

  const options = {
    ...(fixedHeader
      ? { fixedHeader: true, tableBodyHeight: "calc(100vh - 201px)" }
      : {}),
    search: false,
    draggableColumns: { enabled: true },
    selectableRows: "none",
    elevation: 0,
    onTableChange: handleTableChange,
    jumpToPage: true,
    serverSide: true,
    pagination: false,
    count: totalMatches,
    filter: true,
    sort: true,
    customToolbar: () => (
      <IconButton
        name="new_allocation"
        onClick={() => setNewAllocationDialog(true)}
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
              title={title}
              data={allocations || []}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
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

AllocationTable.propTypes = {
  title: PropTypes.string,
  allocations: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      instrument_id: PropTypes.number.isRequired,
      group_id: PropTypes.number.isRequired,
      validity_ranges: PropTypes.arrayOf(
        PropTypes.shape({
          start_date: PropTypes.string.isRequired,
          end_date: PropTypes.string.isRequired,
        }),
      ),
      pi: PropTypes.string.isRequired,
      types: PropTypes.arrayOf(PropTypes.string).isRequired,
      default_share_group_ids: PropTypes.arrayOf(PropTypes.number),
      allocation_users: PropTypes.arrayOf(PropTypes.shape({}).isRequired),
    }),
  ).isRequired,
  instruments: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      telescope_id: PropTypes.number.isRequired,
    }),
  ).isRequired,
  telescopes: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      nickname: PropTypes.string.isRequired,
    }),
  ),
  groups: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
    }),
  ),
  deletePermission: PropTypes.bool,
  paginateCallback: PropTypes.func,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  telescopeInfo: PropTypes.bool,
  fixedHeader: PropTypes.bool,
};

AllocationTable.defaultProps = {
  title: "Allocations",
  groups: [],
  deletePermission: false,
  paginateCallback: null,
  sortingCallback: null,
  totalMatches: 0,
  numPerPage: 10,
  telescopeInfo: true,
  fixedHeader: false,
};

export default AllocationTable;

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
import CircularProgress from "@mui/material/CircularProgress";
import { Link } from "react-router-dom";

import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import DeleteIcon from "@mui/icons-material/Delete";
import * as allocationActions from "../../ducks/allocation";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

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
  groups,
  allocations,
  telescopes,
  instruments,
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

  const [setRowsPerPage] = useState(numPerPage);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [allocationToDelete, setAllocationToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setAllocationToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setAllocationToDelete(null);
  };

  const deleteAllocation = () => {
    dispatch(allocationActions.deleteAllocation(allocationToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Allocation deleted"));
          closeDialog();
        }
      },
    );
  };

  const userLabel = (user) => {
    let label = user.username;
    if (user.first_name && user.last_name) {
      label = `${user.first_name} ${user.last_name} (${user.username})`;
      if (user.contact_email) {
        label = `${label} (${user.contact_email})`;
      }
      if (user.affiliations && user.affiliations.length > 0) {
        label = `${label} (${user.affiliations.join()})`;
      }
    }
    return label;
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
        allocation_users.push(userLabel(user));
      });
    }

    return (
      <div>
        {allocation_users.length > 0 ? allocation_users.join("\n") : ""}
      </div>
    );
  };

  const renderStartDate = (dataIndex) => {
    const allocation = allocations[dataIndex];

    return (
      <div>
        {allocation
          ? new Date(`${allocation.start_date}Z`).toLocaleString("en-US", {
              hour12: false,
            })
          : ""}
      </div>
    );
  };

  const renderEndDate = (dataIndex) => {
    const allocation = allocations[dataIndex];

    return (
      <div>
        {allocation
          ? new Date(`${allocation.end_date}Z`).toLocaleString("en-US", {
              hour12: false,
            })
          : ""}
      </div>
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

  const renderDelete = (dataIndex) => {
    const allocation = allocations[dataIndex];
    return (
      <div>
        <Button
          key={allocation.id}
          id="delete_button"
          classes={{
            root: classes.allocationDelete,
          }}
          onClick={() => openDialog(allocation.id)}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteAllocation}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="allocation"
        />
      </div>
    );
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
  }
  columns.push({
    name: "start_date",
    label: "Start Date",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderStartDate,
    },
  });
  columns.push({
    name: "end_date",
    label: "End Date",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderEndDate,
    },
  });
  columns.push({
    name: "PI",
    label: "PI",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderPI,
    },
  });
  columns.push({
    name: "Group",
    label: "Group",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderGroup,
    },
  });
  columns.push({
    name: "default_share_group",
    label: "Default Share Groups",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderShareGroups,
    },
  });
  columns.push({
    name: "admins",
    label: "Admins",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderAllocationUsers,
    },
  });

  columns.push({
    name: "types",
    label: "Types",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderTypes,
    },
  });
  columns.push({
    name: "delete",
    label: " ",
    options: {
      customBodyRenderLite: renderDelete,
    },
  });

  const options = {
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
  };

  return (
    <div>
      {allocations ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "Allocations" : ""}
                data={allocations}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

AllocationTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  allocations: PropTypes.arrayOf(PropTypes.any).isRequired,
  // eslint-disable-next-line react/forbid-prop-types
  instruments: PropTypes.arrayOf(PropTypes.any).isRequired,
  // eslint-disable-next-line react/forbid-prop-types
  telescopes: PropTypes.arrayOf(PropTypes.any).isRequired,
  // eslint-disable-next-line react/forbid-prop-types
  groups: PropTypes.arrayOf(PropTypes.any),
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  telescopeInfo: PropTypes.bool,
};

AllocationTable.defaultProps = {
  groups: [],
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
  hideTitle: false,
  telescopeInfo: true,
};

export default AllocationTable;

import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import MUIDataTable from "mui-datatables";
import dayjs from "dayjs";

import { showNotification } from "baselayer/components/Notifications";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ModifyAssignment from "./ModifyAssignment";
import * as Actions from "../../ducks/source";
import * as UserActions from "../../ducks/users";

const useStyles = makeStyles((theme) => ({
  assignmentManage: {
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
    overrides: {
      MUIDataTable: {
        paper: {
          width: "100%",
        },
      },
      MUIDataTableBodyCell: {
        stackedCommon: {
          overflow: "hidden",
          "&:last-child": {
            paddingLeft: "0.25rem",
          },
        },
      },
      MUIDataTablePagination: {
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
  });

const AssignmentList = ({ assignments }) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [assignmentToEditDelete, setAssignmentToEditDelete] = useState(null);

  const { users: allUsers } = useSelector((state) => state.users);
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { instrumentList } = useSelector((state) => state.instruments);

  // use useEffect to only send 1 fetchUser per User
  useEffect(() => {
    if (allUsers.length === 0) {
      dispatch(UserActions.fetchUsers());
    }
  }, [allUsers, dispatch]);

  const openEditDialog = (id) => {
    setEditDialogOpen(true);
    setAssignmentToEditDelete(id);
  };
  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setAssignmentToEditDelete(null);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setAssignmentToEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setAssignmentToEditDelete(null);
  };

  const deleteAssignment = () => {
    dispatch(Actions.deleteAssignment(assignmentToEditDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Unassigned target from observing run"));
          closeDeleteDialog();
        }
      },
    );
  };

  if (allUsers.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  if (assignments.length === 0) {
    return <b>No assignments to show for this object...</b>;
  }

  if (observingRunList.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const observingRunDict = {};
  observingRunList.forEach((run) => {
    observingRunDict[run.id] = run;
  });

  assignments.sort((a, b) =>
    observingRunDict[a.run_id]?.calendar_date &&
    observingRunDict[b.run_id]?.calendar_date
      ? dayjs(observingRunDict[a.run_id].calendar_date).unix() -
        dayjs(observingRunDict[b.run_id].calendar_date).unix()
      : 0,
  );

  const renderRunId = (value) => <a href={`/run/${value}`}>{value}</a>;

  const renderRequester = (value, tableMeta) => {
    const { requester_id } = assignments[tableMeta.rowIndex];
    const requester = allUsers.find((user) => user.id === requester_id);
    return requester?.username || "Loading...";
  };

  const renderInstrument = (value, tableMeta) => {
    const { run_id } = assignments[tableMeta.rowIndex];
    const run = observingRunList?.filter((r) => r.id === run_id)[0];
    const instrument_id = run?.instrument_id;
    const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];
    return instrument?.name || "Loading...";
  };

  const renderRunDate = (value, tableMeta) => {
    const { run_id } = assignments[tableMeta.rowIndex];
    const run = observingRunList?.filter((r) => r.id === run_id)[0];
    return run?.calendar_date || "Loading...";
  };

  const renderPI = (value, tableMeta) => {
    const { run_id } = assignments[tableMeta.rowIndex];
    const run = observingRunList?.filter((r) => r.id === run_id)[0];
    return run?.pi || "Loading...";
  };

  const renderManage = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <div className={classes.assignmentManage}>
        <IconButton
          key={`edit_assignment_${assignment.id}`}
          id={`edit_button_assignment_${assignment.id}`}
          onClick={() => openEditDialog(assignment.id)}
        >
          <EditIcon />
        </IconButton>
        <IconButton
          key={`delete_assignment_${assignment.id}`}
          id={`delete_button_assignment_${assignment.id}`}
          onClick={() => openDeleteDialog(assignment.id)}
        >
          <DeleteIcon />
        </IconButton>
      </div>
    );
  };

  const columns = [
    {
      name: "run_id",
      label: "Run Id",
      options: {
        customBodyRender: renderRunId,
      },
    },
    {
      name: "requester",
      label: "Requester",
      options: {
        customBodyRender: renderRequester,
      },
    },
    {
      name: "instrument",
      label: "Instrument",
      options: {
        customBodyRender: renderInstrument,
      },
    },
    {
      name: "runDate",
      label: "Run Date",
      options: {
        customBodyRender: renderRunDate,
      },
    },
    {
      name: "pi",
      label: "PI",
      options: {
        customBodyRender: renderPI,
      },
    },
    { name: "priority", label: "Priority" },
    { name: "status", label: "Status" },
    { name: "comment", label: "Comment" },
    {
      name: "manage",
      label: " ",
      options: {
        customBodyRenderLite: renderManage,
      },
    },
  ];

  const options = {
    filter: false,
    sort: false,
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    elevation: 0,
    rowsPerPageOptions: [1, 10, 15],
  };

  return (
    <div>
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable
            data={assignments}
            options={options}
            columns={columns}
          />
        </ThemeProvider>
      </StyledEngineProvider>
      <Dialog
        open={editDialogOpen && assignmentToEditDelete !== null}
        onClose={closeEditDialog}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
        <DialogTitle>Edit Assignment</DialogTitle>
        <DialogContent dividers>
          <ModifyAssignment
            assignment={assignments.find(
              (a) => a.id === assignmentToEditDelete,
            )}
            onClose={closeEditDialog}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteAssignment}
        dialogOpen={deleteDialogOpen}
        closeDialog={closeDeleteDialog}
        resourceName="assignment"
      />
    </div>
  );
};

AssignmentList.propTypes = {
  assignments: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      requester: PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
      }),
      run: PropTypes.shape({
        pi: PropTypes.string,
        calendar_date: PropTypes.string,
      }),
      priority: PropTypes.string,
      status: PropTypes.string,
      comment: PropTypes.string,
    }),
  ).isRequired,
};

export default AssignmentList;

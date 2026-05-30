import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { makeStyles } from "tss-react/mui";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import dayjs from "dayjs";

import { showNotification } from "baselayer/components/Notifications";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ModifyAssignment from "./ModifyAssignment";
import StyledDataGrid from "../StyledDataGrid";
import * as Actions from "../../ducks/source";
import * as UserActions from "../../ducks/users";

const useStyles = makeStyles()(() => ({
  assignmentManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

const AssignmentList = ({ assignments }) => {
  const { classes } = useStyles();
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

  const runForRow = (row) =>
    observingRunList?.filter((r) => r.id === row.run_id)[0];

  const columns = [
    {
      field: "run_id",
      headerName: "Run Id",
      flex: 1,
      minWidth: 90,
      sortable: false,
      renderCell: (params) => (
        <a href={`/run/${params.value}`}>{params.value}</a>
      ),
    },
    {
      field: "requester",
      headerName: "Requester",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (value, row) =>
        allUsers.find((user) => user.id === row.requester_id)?.username ||
        "Loading...",
    },
    {
      field: "instrument",
      headerName: "Instrument",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (value, row) => {
        const run = runForRow(row);
        const instrument = instrumentList?.filter(
          (i) => i.id === run?.instrument_id,
        )[0];
        return instrument?.name || "Loading...";
      },
    },
    {
      field: "runDate",
      headerName: "Run Date",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (value, row) =>
        runForRow(row)?.calendar_date || "Loading...",
    },
    {
      field: "pi",
      headerName: "PI",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (value, row) => runForRow(row)?.pi || "Loading...",
    },
    {
      field: "priority",
      headerName: "Priority",
      flex: 1,
      minWidth: 90,
      sortable: false,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 100,
      sortable: false,
    },
    {
      field: "comment",
      headerName: "Comment",
      flex: 1,
      minWidth: 140,
      sortable: false,
    },
    {
      field: "manage",
      headerName: " ",
      width: 100,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const assignment = params.row;
        return (
          <div className={classes.assignmentManage}>
            <IconButton
              id={`edit_button_assignment_${assignment.id}`}
              onClick={() => openEditDialog(assignment.id)}
            >
              <EditIcon />
            </IconButton>
            <IconButton
              id={`delete_button_assignment_${assignment.id}`}
              onClick={() => openDeleteDialog(assignment.id)}
            >
              <DeleteIcon />
            </IconButton>
          </div>
        );
      },
    },
  ];

  return (
    <div>
      <StyledDataGrid
        autoHeight
        rows={assignments}
        columns={columns}
        getRowId={(row) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[1, 10, 15]}
        showToolbar
      />
      <Dialog
        open={editDialogOpen && assignmentToEditDelete !== null}
        onClose={closeEditDialog}
        maxWidth="md"
      >
        <DialogTitle>Edit Assignment</DialogTitle>
        <DialogContent dividers>
          {assignments.some((a) => a.id === assignmentToEditDelete) && (
            <ModifyAssignment
              assignment={assignments.find(
                (a) => a.id === assignmentToEditDelete,
              )}
              onClose={closeEditDialog}
            />
          )}
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

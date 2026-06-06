import { useState } from "react";
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
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ModifyAssignment from "./ModifyAssignment";
import StyledDataGrid from "../StyledDataGrid";
import { useDeleteAssignmentMutation } from "../../ducks/source";
import { useGetUsersQuery } from "../../ducks/users";
import { useGetObservingRunsQuery } from "../../ducks/observingRuns";

const useStyles = makeStyles()(() => ({
  assignmentManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

interface AssignmentListProps {
  assignments: any[];
}

const AssignmentList = ({ assignments }: AssignmentListProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [deleteAssignmentMutation] = useDeleteAssignmentMutation();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [assignmentToEditDelete, setAssignmentToEditDelete] =
    useState<any>(null);

  const { data: usersData } = useGetUsersQuery();
  const allUsers = usersData?.users ?? [];
  const { data: observingRunList = [] } = useGetObservingRunsQuery();
  const { instrumentList } = useAppSelector(
    (state) => state["instruments"],
  ) as any;

  const openEditDialog = (id: any) => {
    setEditDialogOpen(true);
    setAssignmentToEditDelete(id);
  };
  const closeEditDialog = () => {
    setEditDialogOpen(false);
    setAssignmentToEditDelete(null);
  };

  const openDeleteDialog = (id: any) => {
    setDeleteDialogOpen(true);
    setAssignmentToEditDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setAssignmentToEditDelete(null);
  };

  const deleteAssignment = () => {
    deleteAssignmentMutation(assignmentToEditDelete)
      .unwrap()
      .then(() => {
        dispatch(showNotification("Unassigned target from observing run"));
        closeDeleteDialog();
      })
      .catch(() => {
        // error notification handled by the baseQuery
      });
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

  const observingRunDict: any = {};
  observingRunList.forEach((run: any) => {
    observingRunDict[run.id] = run;
  });

  assignments.sort((a, b) =>
    observingRunDict[a.run_id]?.calendar_date &&
    observingRunDict[b.run_id]?.calendar_date
      ? dayjs(observingRunDict[a.run_id].calendar_date).unix() -
        dayjs(observingRunDict[b.run_id].calendar_date).unix()
      : 0,
  );

  const runForRow = (row: any) =>
    observingRunList?.filter((r: any) => r.id === row.run_id)[0];

  const columns: any[] = [
    {
      field: "run_id",
      headerName: "Run Id",
      flex: 1,
      minWidth: 90,
      sortable: false,
      renderCell: (params: any) => (
        <a href={`/run/${params.value}`}>{params.value}</a>
      ),
    },
    {
      field: "requester",
      headerName: "Requester",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (_value: any, row: any) =>
        allUsers.find((user: any) => user.id === row.requester_id)?.username ||
        "Loading...",
    },
    {
      field: "instrument",
      headerName: "Instrument",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (_value: any, row: any) => {
        const run = runForRow(row);
        const instrument = instrumentList?.filter(
          (i: any) => i.id === run?.["instrument_id"],
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
      valueGetter: (_value: any, row: any) =>
        runForRow(row)?.["calendar_date"] || "Loading...",
    },
    {
      field: "pi",
      headerName: "PI",
      flex: 1,
      minWidth: 120,
      sortable: false,
      valueGetter: (_value: any, row: any) =>
        runForRow(row)?.["pi"] || "Loading...",
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
      renderCell: (params: any) => {
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
        getRowId={(row: any) => row.id}
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

export default AssignmentList;

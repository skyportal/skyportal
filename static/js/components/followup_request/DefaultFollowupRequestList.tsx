import { useState } from "react";
import { Link } from "react-router-dom";
import { makeStyles } from "tss-react/mui";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { JSONTree } from "react-json-tree";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import NewDefaultFollowupRequest from "./NewDefaultFollowupRequest";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import * as defaultFollowupRequestsActions from "../../ducks/default_followup_requests";
import { useGetGroupsQuery } from "../../ducks/groups";

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  defaultFollowupRequestManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
}));

interface DefaultFollowupRequestListProps {
  default_followup_requests: any[];
  deletePermission: boolean;
}

const DefaultFollowupRequestList = ({
  default_followup_requests,
  deletePermission,
}: DefaultFollowupRequestListProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();
  const { instrumentList } = useAppSelector(
    (state) => (state as any).instruments,
  );
  const { telescopeList } = useAppSelector(
    (state) => (state as any).telescopes,
  );
  const groups = useGetGroupsQuery().data?.all ?? null;

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDeleteDialog = (id: any) => {
    setDeleteDialogOpen(true);
    setDefaultFollowupRequestToDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setDefaultFollowupRequestToDelete(null);
  };

  const [defaultFollowupRequestToDelete, setDefaultFollowupRequestToDelete] =
    useState<any>(null);

  const deleteDefaultFollowupRequest = () => {
    dispatch(
      defaultFollowupRequestsActions.deleteDefaultFollowupRequest(
        defaultFollowupRequestToDelete,
      ),
    ).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification("Default follow-up request deleted"));
        closeDeleteDialog();
      }
    });
  };

  const renderInstrumentName = (params: any) => {
    const { allocation } = params.row;
    const { instrument_id } = allocation;
    const instrument = instrumentList?.filter(
      (i: any) => i.id === instrument_id,
    )[0];
    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {instrument ? instrument.name : ""}
        </Link>
      </div>
    );
  };

  const renderTelescopeName = (params: any) => {
    const { allocation } = params.row;
    const { instrument_id } = allocation;
    const instrument = instrumentList?.filter(
      (i: any) => i.id === instrument_id,
    )[0];
    const telescope_id = instrument?.telescope_id;
    const telescope = telescopeList?.filter(
      (t: any) => t.id === telescope_id,
    )[0];
    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {telescope ? telescope.nickname : ""}
        </Link>
      </div>
    );
  };

  const renderGroup = (params: any) => {
    const { allocation } = params.row;
    const group = groups?.filter((g: any) => g.id === allocation.group_id)[0];
    return <div>{group ? group.name : ""}</div>;
  };

  const renderPayload = (params: any) => {
    const cellStyle = { whiteSpace: "nowrap" as const };
    return (
      <div style={cellStyle}>
        {params.row ? <JSONTree data={params.row.payload} hideRoot /> : ""}
      </div>
    );
  };

  const renderSourceFilter = (params: any) => {
    const cellStyle = { whiteSpace: "nowrap" as const };
    return (
      <div style={cellStyle}>
        {params.row ? (
          <JSONTree data={params.row.source_filter} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };

  const renderManage = (params: any) => {
    if (!deletePermission) {
      return null;
    }
    const default_followup_request = params.row;
    return (
      <div className={classes.defaultFollowupRequestManage}>
        <Button
          id={`delete_button_${default_followup_request.id}`}
          onClick={() => openDeleteDialog(default_followup_request.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns: any[] = [
    {
      field: "instrument_name",
      headerName: "Instrument Name",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderInstrumentName,
    },
    {
      field: "telescope_name",
      headerName: "Telescope Name",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderTelescopeName,
    },
    {
      field: "default_followup_name",
      headerName: "Name",
      flex: 1,
      minWidth: 120,
    },
    {
      field: "group",
      headerName: "Group",
      flex: 1,
      minWidth: 120,
      sortable: false,
      renderCell: renderGroup,
    },
    {
      field: "Payload",
      headerName: "Payload",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderPayload,
    },
    {
      field: "Source Filter",
      headerName: "Source Filter",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderSourceFilter,
    },
    {
      field: "manage",
      headerName: " ",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ];

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <IconButton
        name="new_default_followup_request"
        onClick={() => openNewDialog()}
      >
        <AddIcon />
      </IconButton>
    </GridToolbarContainer>
  );

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6" sx={{ p: 1 }}>
          Default Follow-up Requests
        </Typography>
        <StyledDataGrid
          autoHeight
          rows={default_followup_requests || []}
          columns={columns}
          getRowId={(row: any) => row.id}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Paper>
      <Dialog open={newDialogOpen} onClose={closeNewDialog} maxWidth="md">
        <DialogTitle>New Default Follow-up Request</DialogTitle>
        <DialogContent dividers>
          <NewDefaultFollowupRequest
            {...({ onClose: closeNewDialog } as any)}
          />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteDefaultFollowupRequest}
        dialogOpen={deleteDialogOpen}
        closeDialog={closeDeleteDialog}
        resourceName="default follow-up request"
      />
    </div>
  );
};

export default DefaultFollowupRequestList;

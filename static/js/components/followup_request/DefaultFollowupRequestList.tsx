import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import { JSONTree } from "react-json-tree";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import NewDefaultFollowupRequest from "./NewDefaultFollowupRequest";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

import { useDeleteDefaultFollowupRequestMutation } from "../../ducks/default_followup_requests";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useIsReadOnly } from "../../ducks/profile";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

interface DefaultFollowupRequestListProps {
  default_followup_requests: any[];
  deletePermission: boolean;
}

const ExpandableCell = ({ children, maxHeight = 80 }: any) => {
  const [expanded, setExpanded] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) setOverflows(ref.current.scrollHeight > maxHeight);
  }, [children]);

  return (
    <Box sx={{ display: "flex", alignItems: "flex-start", gap: 0.5 }}>
      <Box
        ref={ref}
        sx={{
          flex: 1,
          overflow: "hidden",
          maxHeight: expanded ? "none" : maxHeight,
        }}
      >
        {children}
      </Box>
      {(overflows || expanded) && (
        <IconButton size="small" onClick={() => setExpanded((e) => !e)}>
          {expanded ? (
            <ExpandLessIcon fontSize="small" />
          ) : (
            <ExpandMoreIcon fontSize="small" />
          )}
        </IconButton>
      )}
    </Box>
  );
};

const DefaultFollowupRequestList = ({
  default_followup_requests,
  deletePermission,
}: DefaultFollowupRequestListProps) => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all ?? null;
  const [deleteDefaultFollowupRequestMutation] =
    useDeleteDefaultFollowupRequestMutation();

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
    deleteDefaultFollowupRequestMutation(defaultFollowupRequestToDelete)
      .unwrap()
      .then(() => {
        dispatch(showNotification("Default follow-up request deleted"));
        closeDeleteDialog();
      })
      .catch(() => {});
  };

  const renderAllocationName = (params: any) => {
    const allocation = params.value;
    if (!allocation) return null;
    const instrument = instrumentList?.find(
      (i) => i.id === allocation.instrument_id,
    );
    return (
      <Tooltip
        title={
          <>
            PI: {allocation?.["pi"] || ""}
            <br />
            Proposal: {allocation?.["proposal_id"] || ""}
            <br />
            Instrument: {instrument?.["name"] || ""}
            <br />
          </>
        }
      >
        <Link
          to={`/allocation/${allocation.id}`}
          style={{ display: "flex", flexDirection: "column" }}
        >
          {allocation?.["pi"] || ""} / {instrument?.["name"] || ""}
        </Link>
      </Tooltip>
    );
  };

  const renderTelescopeNickname = (params: any) => {
    const allocation = params.row.allocation;
    if (!allocation) return null;
    const instrument = instrumentList?.find(
      (i) => i.id === allocation.instrument_id,
    );
    const telescope = telescopeList?.find(
      (t: any) => t.id === instrument?.["telescope_id"],
    );
    return (
      <Link to={`/telescope/${instrument?.telescope_id}`}>
        {telescope?.["nickname"] || ""}
      </Link>
    );
  };

  const renderGroup = (params: any) => {
    const { allocation } = params.row;
    const group = groups?.find((g: any) => g.id === allocation.group_id);
    return group?.name !== undefined && <Chip label={group.name} />;
  };

  const renderPayload = (params: any) =>
    params.row ? (
      <ExpandableCell>
        <JSONTree data={params.row.payload} hideRoot />
      </ExpandableCell>
    ) : (
      ""
    );

  const renderSourceFilter = (params: any) =>
    params.row ? (
      <ExpandableCell>
        <JSONTree data={params.row.source_filter} hideRoot />
      </ExpandableCell>
    ) : (
      ""
    );

  const renderManage = (params: any) => {
    if (!deletePermission) return null;
    const default_followup_request = params.row;
    return (
      <IconButton
        color="error"
        onClick={() => openDeleteDialog(default_followup_request.id)}
      >
        <DeleteIcon />
      </IconButton>
    );
  };

  const columns: any[] = [
    {
      field: "allocation",
      headerName: "Allocation",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderAllocationName,
    },
    {
      field: "telescope_nickname",
      headerName: "Telescope",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: renderTelescopeNickname,
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
    deletePermission && {
      field: "manage",
      headerName: " ",
      minWidth: 60,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    },
  ].filter(Boolean);

  const CustomToolbar = () => (
    <DataGridToolbar showQuickFilter={false} showExport>
      {!isReadOnly && (
        <IconButton
          name="new_default_followup_request"
          onClick={() => openNewDialog()}
        >
          <AddIcon />
        </IconButton>
      )}
    </DataGridToolbar>
  );

  return (
    <Box>
      <StyledDataGrid
        autoHeight
        getRowHeight={() => "auto"}
        rows={default_followup_requests || []}
        columns={columns}
        getRowId={(row: any) => row.id}
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
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
    </Box>
  );
};

export default DefaultFollowupRequestList;

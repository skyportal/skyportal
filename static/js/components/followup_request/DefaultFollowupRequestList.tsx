import { useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useDeleteDefaultFollowupRequestMutation } from "../../ducks/default_followup_requests";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useIsReadOnly } from "../../ducks/profile";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT_WITH_TABS,
} from "../StyledDataGrid";
import NewDefaultFollowupRequest from "./NewDefaultFollowupRequest";
import JsonCell from "./JsonCell";
import { PLAIN_LINKS_SX } from "./columns";

const DefaultFollowupRequestToolbar = ({ onAdd }: { onAdd?: () => void }) => (
  <DataGridToolbar
    showQuickFilter={false}
    title="Default Follow-up Requests"
    showExpandAll
  >
    {onAdd && (
      <IconButton name="new_default_followup_request" onClick={onAdd}>
        <AddIcon />
      </IconButton>
    )}
  </DataGridToolbar>
);

interface DefaultFollowupRequestListProps {
  default_followup_requests: any[];
  deletePermission: boolean;
}

const DefaultFollowupRequestList = ({
  default_followup_requests,
  deletePermission,
}: DefaultFollowupRequestListProps) => {
  const dispatch = useAppDispatch();
  const isReadOnly = useIsReadOnly();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all;
  const [deleteDefaultFollowupRequestMutation] =
    useDeleteDefaultFollowupRequestMutation();
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [idToDelete, setIdToDelete] = useState<number | null>(null);

  const deleteDefaultFollowupRequest = () =>
    deleteDefaultFollowupRequestMutation(idToDelete!)
      .unwrap()
      .then(() => {
        dispatch(showNotification("Default follow-up request deleted"));
        setIdToDelete(null);
      })
      .catch(() => {});

  const instrumentOf = (allocation: any) =>
    instrumentList.find(({ id }) => id === allocation.instrument_id);

  const columns: any[] = [
    {
      field: "allocation",
      headerName: "Allocation",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: ({ value: allocation }: any) => {
        if (!allocation) return null;
        const instrument = instrumentOf(allocation);
        return (
          <Tooltip
            title={
              <Box sx={{ display: "flex", flexDirection: "column" }}>
                <span>PI: {allocation.pi}</span>
                <span>Proposal: {allocation.proposal_id}</span>
                <span>Instrument: {instrument?.name}</span>
              </Box>
            }
          >
            <Link to={`/allocation/${allocation.id}`}>
              {allocation.pi} / {instrument?.name}
            </Link>
          </Tooltip>
        );
      },
    },
    {
      field: "telescope_nickname",
      headerName: "Telescope",
      flex: 1,
      minWidth: 140,
      sortable: false,
      renderCell: ({ row }: any) => {
        if (!row.allocation) return null;
        const instrument = instrumentOf(row.allocation);
        return (
          <Link to={`/telescope/${instrument?.telescope_id}`}>
            {
              telescopeList.find(
                ({ id }: any) => id === instrument?.telescope_id,
              )?.nickname
            }
          </Link>
        );
      },
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
      renderCell: ({ row }: any) => {
        const group = groups?.find(({ id }) => id === row.allocation.group_id);
        return group?.name ? (
          <Chip
            label={group.name}
            component={Link}
            to={`/group/${group.id}`}
            clickable
          />
        ) : null;
      },
    },
    {
      field: "Payload",
      headerName: "Payload",
      flex: 2,
      minWidth: 320,
      sortable: false,
      renderCell: ({ row }: any) => <JsonCell data={row.payload} />,
    },
    {
      field: "Source Filter",
      headerName: "Source Filter",
      flex: 2,
      minWidth: 320,
      sortable: false,
      renderCell: ({ row }: any) => <JsonCell data={row.source_filter} />,
    },
    deletePermission && {
      field: "manage",
      headerName: " ",
      minWidth: 60,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) => (
        <IconButton color="error" onClick={() => setIdToDelete(row.id)}>
          <DeleteIcon />
        </IconButton>
      ),
    },
  ].filter(Boolean);

  return (
    <>
      <StyledDataGrid
        height={FULL_PAGE_HEIGHT_WITH_TABS}
        getRowHeight={() => "auto"}
        sx={PLAIN_LINKS_SX}
        rows={default_followup_requests}
        columns={columns}
        slots={{ toolbar: DefaultFollowupRequestToolbar }}
        slotProps={{
          toolbar: {
            onAdd: isReadOnly ? undefined : () => setNewDialogOpen(true),
          },
        }}
        showToolbar
      />
      <Dialog
        open={newDialogOpen}
        onClose={() => setNewDialogOpen(false)}
        maxWidth="md"
      >
        <DialogTitle>New Default Follow-up Request</DialogTitle>
        <DialogContent dividers>
          <NewDefaultFollowupRequest />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteDefaultFollowupRequest}
        dialogOpen={idToDelete !== null}
        closeDialog={() => setIdToDelete(null)}
        resourceName="default follow-up request"
      />
    </>
  );
};

export default DefaultFollowupRequestList;

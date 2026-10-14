import { useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import ButtonGroup from "@mui/material/ButtonGroup";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

import {
  useGetGroupAdmissionRequestsQuery,
  useUpdateAdmissionRequestStatusMutation,
} from "../../ducks/groupAdmissionRequests";
import { useAddGroupUserMutation } from "../../ducks/groups";
import { groupApi } from "../../ducks/group";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const STATUS_COLORS: Record<string, "success" | "warning" | "error"> = {
  accepted: "success",
  pending: "warning",
  declined: "error",
};

const AdmissionRequestsToolbar = ({
  acceptedCount,
  showAccepted,
  setShowAccepted,
}: {
  acceptedCount: number;
  showAccepted: boolean;
  setShowAccepted: (show: boolean) => void;
}) => (
  <DataGridToolbar title="Admission requests">
    {acceptedCount > 0 && (
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={showAccepted}
            onChange={(event) => setShowAccepted(event.target.checked)}
          />
        }
        label={`Show accepted (${acceptedCount})`}
        sx={{ mx: 1 }}
      />
    )}
  </DataGridToolbar>
);

const toRow = (request: any) => ({
  ...request,
  name: [request.user?.first_name, request.user?.last_name]
    .filter(Boolean)
    .join(" "),
  username: request.user?.username,
  affiliations: (request.user?.affiliations ?? []).join(", "),
  contact_email: request.user?.contact_email,
});

const GroupAdmissionRequestsManagement = ({ groupID }: { groupID: number }) => {
  const dispatch = useAppDispatch();
  const [showAccepted, setShowAccepted] = useState(false);
  const { data: requests } = useGetGroupAdmissionRequestsQuery(groupID);
  const [updateStatus] = useUpdateAdmissionRequestStatusMutation();
  const [addGroupUser] = useAddGroupUserMutation();

  if (requests == null) return null;

  const acceptRequest = async (request: any) => {
    const added = await addGroupUser({
      userID: request.user_id,
      admin: false,
      group_id: groupID,
    } as any);
    if (added.error) return;
    const { error } = await updateStatus({
      requestID: request.id,
      status: "accepted",
    });
    if (error) return;
    dispatch(showNotification("Successfully admitted user to group."));
    dispatch(groupApi.util.invalidateTags([{ type: "Group", id: groupID }]));
  };

  const declineRequest = async (request: any) => {
    const { error } = await updateStatus({
      requestID: request.id,
      status: "declined",
    });
    if (!error) dispatch(showNotification("Successfully declined request."));
  };

  const renderActions = ({ row }: any) =>
    row.status !== "accepted" && (
      <ButtonGroup>
        <Button
          primary
          size="small"
          onClick={() => acceptRequest(row)}
          data-testid={`acceptRequestButton${row.user_id}`}
        >
          Accept
        </Button>
        {row.status === "pending" && (
          <Button
            secondary
            size="small"
            onClick={() => declineRequest(row)}
            data-testid={`declineRequestButton${row.user_id}`}
          >
            Decline
          </Button>
        )}
      </ButtonGroup>
    );

  const allRows = requests.map(toRow);
  const acceptedCount = allRows.filter(
    (row: any) => row.status === "accepted",
  ).length;

  const columns: any[] = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 140 },
    {
      field: "username",
      headerName: "Username",
      flex: 1,
      minWidth: 120,
      renderCell: ({ row }: any) => (
        <Link to={`/user/${row.user_id}`}>{row.username}</Link>
      ),
    },
    {
      field: "affiliations",
      headerName: "Affiliations",
      flex: 1,
      minWidth: 160,
    },
    { field: "contact_email", headerName: "Email", flex: 1, minWidth: 160 },
    {
      field: "message",
      headerName: "Reason",
      flex: 2,
      minWidth: 220,
      renderCell: ({ value }: any) => (
        <Box sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {value}
        </Box>
      ),
    },
    {
      field: "created_at",
      headerName: "Requested",
      flex: 1,
      minWidth: 130,
      renderCell: ({ value }: any) => dayjs().to(dayjs.utc(`${value}Z`)),
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 100,
      renderCell: ({ value }: any) => (
        <Chip
          size="small"
          variant="outlined"
          label={value}
          color={STATUS_COLORS[value]}
        />
      ),
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      renderCell: renderActions,
    },
  ];

  return (
    <StyledDataGrid
      autoHeight
      rows={
        showAccepted
          ? allRows
          : allRows.filter((row: any) => row.status !== "accepted")
      }
      columns={columns}
      getRowHeight={() => "auto"}
      initialState={{
        columns: {
          columnVisibilityModel: {
            name: allRows.some((row: any) => row.name),
            contact_email: allRows.some((row: any) => row.contact_email),
          },
        },
        sorting: { sortModel: [{ field: "created_at", sort: "desc" }] },
      }}
      showToolbar
      slots={{ toolbar: AdmissionRequestsToolbar }}
      slotProps={{ toolbar: { acceptedCount, showAccepted, setShowAccepted } }}
    />
  );
};

export default GroupAdmissionRequestsManagement;

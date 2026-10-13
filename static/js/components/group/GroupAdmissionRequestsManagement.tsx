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

const statusColor = (status: string) => {
  if (status === "accepted") return "success";
  if (status === "pending") return "warning";
  return "error";
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

interface GroupAdmissionRequestsManagementProps {
  groupID: number;
}

const GroupAdmissionRequestsManagement = ({
  groupID,
}: GroupAdmissionRequestsManagementProps) => {
  const dispatch = useAppDispatch();
  const [showAccepted, setShowAccepted] = useState(false);

  const { data: requests } = useGetGroupAdmissionRequestsQuery(groupID, {
    skip: !groupID,
  });
  const [updateAdmissionRequestStatus] =
    useUpdateAdmissionRequestStatusMutation();
  const [addGroupUser] = useAddGroupUserMutation();

  if (requests == null) {
    return <></>;
  }

  const handleAcceptRequest = async ({
    requestID,
    userID,
  }: {
    requestID: number;
    userID: number;
  }) => {
    try {
      await addGroupUser({
        userID,
        admin: false,
        group_id: groupID,
      } as any).unwrap();
    } catch {
      return;
    }
    try {
      await updateAdmissionRequestStatus({
        requestID,
        status: "accepted",
      }).unwrap();
      dispatch(showNotification("Successfully admitted user to group."));
      dispatch(groupApi.util.invalidateTags([{ type: "Group", id: groupID }]));
    } catch {
      // error notification handled by the base query
    }
  };

  const handleDeclineRequest = async ({ requestID }: { requestID: number }) => {
    try {
      await updateAdmissionRequestStatus({
        requestID,
        status: "declined",
      }).unwrap();
      dispatch(showNotification("Successfully declined request."));
    } catch {
      // error notification handled by the base query
    }
  };

  const renderActions = (params: any) => {
    const request = params.row;
    if (request.status === "pending") {
      return (
        <ButtonGroup>
          <Button
            primary
            size="small"
            onClick={() =>
              handleAcceptRequest({
                requestID: request.id,
                userID: request.user_id,
              })
            }
            data-testid={`acceptRequestButton${request.user_id}`}
          >
            Accept
          </Button>
          <Button
            secondary
            size="small"
            onClick={() => handleDeclineRequest({ requestID: request.id })}
            data-testid={`declineRequestButton${request.user_id}`}
          >
            Decline
          </Button>
        </ButtonGroup>
      );
    }
    if (request.status === "declined") {
      return (
        <Button
          primary
          size="small"
          onClick={() =>
            handleAcceptRequest({
              requestID: request.id,
              userID: request.user_id,
            })
          }
          data-testid={`acceptRequestButton${request.user_id}`}
        >
          Accept
        </Button>
      );
    }
    return <></>;
  };

  const acceptedCount = requests.filter(
    (request: any) => request.status === "accepted",
  ).length;
  const rows = requests
    .filter((request: any) => showAccepted || request.status !== "accepted")
    .map((request: any) => ({
      ...request,
      name: [request.user?.first_name, request.user?.last_name]
        .filter(Boolean)
        .join(" "),
      username: request.user?.username,
      affiliations: (request.user?.affiliations ?? []).join(", "),
      contact_email: request.user?.contact_email,
    }));
  const hasNames = requests.some(
    (request: any) => request.user?.first_name || request.user?.last_name,
  );
  const hasEmails = requests.some(
    (request: any) => request.user?.contact_email,
  );

  const columns: any[] = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 140 },
    {
      field: "username",
      headerName: "Username",
      flex: 1,
      minWidth: 120,
      renderCell: (params: any) => (
        <Link to={`/user/${params.row.user_id}`}>{params.row.username}</Link>
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
      renderCell: (params: any) => (
        <Box sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {params.value}
        </Box>
      ),
    },
    {
      field: "created_at",
      headerName: "Requested",
      flex: 1,
      minWidth: 130,
      renderCell: (params: any) =>
        params.value ? dayjs().to(dayjs.utc(`${params.value}Z`)) : "",
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 100,
      renderCell: (params: any) => (
        <Chip
          size="small"
          variant="outlined"
          label={params.value}
          color={statusColor(params.value)}
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
      rows={rows}
      columns={columns}
      getRowId={(row: any) => row.id}
      getRowHeight={() => "auto"}
      initialState={{
        columns: {
          columnVisibilityModel: { name: hasNames, contact_email: hasEmails },
        },
        sorting: { sortModel: [{ field: "created_at", sort: "desc" }] },
      }}
      showToolbar
      slots={{ toolbar: AdmissionRequestsToolbar }}
      slotProps={{
        toolbar: { acceptedCount, showAccepted, setShowAccepted },
      }}
    />
  );
};

export default GroupAdmissionRequestsManagement;

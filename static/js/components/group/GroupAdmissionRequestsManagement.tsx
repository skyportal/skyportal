import Box from "@mui/material/Box";
import ButtonGroup from "@mui/material/ButtonGroup";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import {
  useGetGroupAdmissionRequestsQuery,
  useUpdateAdmissionRequestStatusMutation,
} from "../../ducks/groupAdmissionRequests";
import { useAddGroupUserMutation } from "../../ducks/groups";
import { groupApi } from "../../ducks/group";

const renderUserInfo = (value: any) => {
  let userInfoString = value.username;
  if (!!value.first_name && !!value.last_name) {
    userInfoString += ` (${value.first_name} ${value.last_name})`;
  }
  return userInfoString;
};

interface GroupAdmissionRequestsManagementProps {
  groupID: number;
}

const GroupAdmissionRequestsManagement = ({
  groupID,
}: GroupAdmissionRequestsManagementProps) => {
  const dispatch = useAppDispatch();

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

  const columns: any[] = [
    {
      field: "user",
      headerName: "Requesting User",
      flex: 1,
      minWidth: 180,
      valueGetter: (_value: any, row: any) => renderUserInfo(row.user),
    },
    { field: "status", headerName: "Status", flex: 1, minWidth: 120 },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      renderCell: renderActions,
    },
  ];

  return (
    <Box sx={{ width: "100%" }}>
      <Typography variant="h6">Admission requests</Typography>
      <StyledDataGrid
        autoHeight
        rows={requests}
        columns={columns}
        getRowId={(row: any) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[10, 25, 50, 100, 200]}
        showToolbar
      />
    </Box>
  );
};

export default GroupAdmissionRequestsManagement;

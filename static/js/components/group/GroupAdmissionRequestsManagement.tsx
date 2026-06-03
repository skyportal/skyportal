import { useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import * as groupAdmissionRequestsActions from "../../ducks/groupAdmissionRequests";
import * as groupsActions from "../../ducks/groups";
import * as groupActions from "../../ducks/group";

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

  useEffect(() => {
    if (groupID) {
      dispatch(
        groupAdmissionRequestsActions.fetchGroupAdmissionRequests(groupID),
      );
    }
  }, [groupID, dispatch]);

  const groupAdmissionRequests = useAppSelector(
    (state) => state["groupAdmissionRequests"],
  );
  if (
    !groupAdmissionRequests ||
    !Object.keys(groupAdmissionRequests)
      .map((k) => String(k))
      .includes(String(groupID))
  ) {
    return <></>;
  }
  const requests = (groupAdmissionRequests as Record<string, any>)[groupID];

  const handleAcceptRequest = async ({
    requestID,
    userID,
  }: {
    requestID: number;
    userID: number;
  }) => {
    const addGroupUserResult: any = await dispatch(
      groupsActions.addGroupUser({
        userID,
        admin: false,
        group_id: groupID,
      } as any),
    );
    const updateAdmissionRequestStatusResult: any = await dispatch(
      groupAdmissionRequestsActions.updateAdmissionRequestStatus({
        requestID,
        status: "accepted",
      }),
    );
    if (
      addGroupUserResult.status === "success" &&
      updateAdmissionRequestStatusResult.status === "success"
    ) {
      dispatch(showNotification("Successfully admitted user to group."));
      dispatch(groupsActions.fetchGroups(true));
      dispatch(groupActions.fetchGroup(groupID));
      dispatch(
        groupAdmissionRequestsActions.fetchGroupAdmissionRequests(groupID),
      );
    }
  };

  const handleDeclineRequest = async ({ requestID }: { requestID: number }) => {
    const updateAdmissionRequestStatusResult: any = await dispatch(
      groupAdmissionRequestsActions.updateAdmissionRequestStatus({
        requestID,
        status: "declined",
      }),
    );
    if (updateAdmissionRequestStatusResult.status === "success") {
      dispatch(showNotification("Successfully declined request."));
      dispatch(
        groupAdmissionRequestsActions.fetchGroupAdmissionRequests(groupID),
      );
    }
  };

  const renderActions = (params: any) => {
    const request = params.row;
    if (request.status === "pending") {
      return (
        <>
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
        </>
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

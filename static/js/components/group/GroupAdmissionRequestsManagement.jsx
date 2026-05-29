import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import * as groupAdmissionRequestsActions from "../../ducks/groupAdmissionRequests";
import * as groupsActions from "../../ducks/groups";
import * as groupActions from "../../ducks/group";

const renderUserInfo = (value) => {
  let userInfoString = value.username;
  if (!!value.first_name && !!value.last_name) {
    userInfoString += ` (${value.first_name} ${value.last_name})`;
  }
  return userInfoString;
};

const GroupAdmissionRequestsManagement = ({ groupID }) => {
  const dispatch = useDispatch();

  useEffect(() => {
    if (groupID) {
      dispatch(
        groupAdmissionRequestsActions.fetchGroupAdmissionRequests(groupID),
      );
    }
  }, [groupID, dispatch]);

  const groupAdmissionRequests = useSelector(
    (state) => state.groupAdmissionRequests,
  );
  if (
    !groupAdmissionRequests ||
    !Object.keys(groupAdmissionRequests)
      .map((k) => String(k))
      .includes(String(groupID))
  ) {
    return <></>;
  }
  const requests = groupAdmissionRequests[groupID];

  const handleAcceptRequest = async ({ requestID, userID }) => {
    const addGroupUserResult = await dispatch(
      groupsActions.addGroupUser({ userID, admin: false, group_id: groupID }),
    );
    const updateAdmissionRequestStatusResult = await dispatch(
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

  const handleDeclineRequest = async ({ requestID }) => {
    const updateAdmissionRequestStatusResult = await dispatch(
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

  const renderActions = (params) => {
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

  const columns = [
    {
      field: "user",
      headerName: "Requesting User",
      flex: 1,
      minWidth: 180,
      valueGetter: (value, row) => renderUserInfo(row.user),
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
        getRowId={(row) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[10, 25, 50, 100, 200]}
        showToolbar
      />
    </Box>
  );
};

GroupAdmissionRequestsManagement.propTypes = {
  groupID: PropTypes.number.isRequired,
};

export default GroupAdmissionRequestsManagement;

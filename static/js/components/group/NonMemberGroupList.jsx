import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import * as groupAdmissionRequestsActions from "../../ducks/groupAdmissionRequests";

const NonMemberGroupList = ({ groups }) => {
  const dispatch = useDispatch();
  const { id: currentUserID, groupAdmissionRequests } = useSelector(
    (state) => state.profile,
  );
  if (currentUserID === null) {
    return <CircularProgress color="secondary" />;
  }
  const pendingRequestGroupIDs = groupAdmissionRequests
    ?.filter((request) => request.status === "pending")
    ?.map((request) => request.group_id);
  const declinedRequestGroupIDs = groupAdmissionRequests
    ?.filter((request) => request.status === "declined")
    ?.map((request) => request.group_id);

  const handleRequestAdmission = async (groupID) => {
    const result = await dispatch(
      groupAdmissionRequestsActions.requestGroupAdmission(
        currentUserID,
        groupID,
      ),
    );
    if (result.status === "success") {
      dispatch(showNotification("Successfully requested admission to group."));
    }
  };

  const handleDeleteAdmissionRequest = (admissionRequestID) => {
    dispatch(
      groupAdmissionRequestsActions.deleteAdmissionRequest(admissionRequestID),
    );
  };

  const renderActions = (params) => {
    const group = params.row;
    if (declinedRequestGroupIDs.includes(group.id)) {
      return <em>Admission request declined.</em>;
    }
    if (pendingRequestGroupIDs.includes(group.id)) {
      const admissionRequestID = groupAdmissionRequests?.filter(
        (request) => request.group_id === group.id,
      )[0]?.id;
      return (
        <>
          <em>Request pending...</em>
          <br />
          <Button
            secondary
            size="small"
            onClick={() => handleDeleteAdmissionRequest(admissionRequestID)}
            data-testid={`deleteAdmissionRequestButton${group.id}`}
          >
            Delete request
          </Button>
        </>
      );
    }
    return (
      <Button
        secondary
        size="small"
        onClick={() => handleRequestAdmission(group.id)}
        data-testid={`requestAdmissionButton${group.id}`}
      >
        Request admission
      </Button>
    );
  };

  const columns = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 120 },
    { field: "nickname", headerName: "Nickname", flex: 1, minWidth: 120 },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: renderActions,
    },
  ];

  return (
    <Box sx={{ width: "100%" }}>
      <Typography variant="h6">Non-member groups</Typography>
      <StyledDataGrid
        autoHeight
        rows={groups}
        columns={columns}
        getRowId={(row) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[10, 25, 50, 100, 200]}
        showToolbar
      />
    </Box>
  );
};

NonMemberGroupList.propTypes = {
  groups: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      nickname: PropTypes.string,
      id: PropTypes.number,
    }),
  ).isRequired,
};

export default NonMemberGroupList;

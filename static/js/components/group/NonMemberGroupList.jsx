import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import MUIDataTable from "mui-datatables";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import * as groupAdmissionRequestsActions from "../../ducks/groupAdmissionRequests";

const NonMemberGroupList = ({ groups }) => {
  const dispatch = useDispatch();
  const { id: currentUserID, groupAdmissionRequests } = useSelector(
    (state) => state.profile,
  );
  if (currentUserID === null) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
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

  const renderActions = (dataIndex) => {
    const group = groups[dataIndex];
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
    {
      name: "name",
      label: "Name",
      options: {
        filter: false,
      },
    },
    {
      name: "nickname",
      label: "Nickname",
      options: {
        filter: false,
      },
    },
    {
      name: "actions",
      label: "Actions",
      options: {
        sort: false,
        customBodyRenderLite: renderActions,
        filter: false,
      },
    },
  ];

  const options = {
    responsive: "standard",
    download: false,
    search: true,
    selectableRows: "none",
    rowsPerPage: 10,
    rowsPerPageOptions: [10, 25, 50, 100, 200],
    filter: false,
    jumpToPage: true,
    pagination: true,
    rowHover: false,
    print: false,
    elevation: 1,
  };
  return (
    <MUIDataTable
      title="Non-member groups"
      columns={columns}
      data={groups}
      options={options}
    />
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

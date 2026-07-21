import { useGetProfileQuery } from "../../ducks/profile";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import {
  useRequestGroupAdmissionMutation,
  useDeleteAdmissionRequestMutation,
} from "../../ducks/groupAdmissionRequests";

interface NonMemberGroup {
  name?: string;
  nickname?: string | null;
  id?: number;
  auto_accept_requests?: boolean;
}

interface NonMemberGroupListProps {
  groups: NonMemberGroup[];
}

const NonMemberGroupList = ({ groups }: NonMemberGroupListProps) => {
  const dispatch = useAppDispatch();
  const [requestGroupAdmission] = useRequestGroupAdmissionMutation();
  const [deleteAdmissionRequest] = useDeleteAdmissionRequestMutation();
  const { id: currentUserID, groupAdmissionRequests } =
    (useGetProfileQuery().data as any) ?? {};
  if (currentUserID === null || currentUserID === undefined) {
    return <CircularProgress color="secondary" />;
  }
  const pendingRequestGroupIDs = groupAdmissionRequests
    ?.filter((request: any) => request.status === "pending")
    ?.map((request: any) => request.group_id);
  const declinedRequestGroupIDs = groupAdmissionRequests
    ?.filter((request: any) => request.status === "declined")
    ?.map((request: any) => request.group_id);

  const handleRequestAdmission = async (group: NonMemberGroup) => {
    try {
      await requestGroupAdmission({
        userID: currentUserID,
        groupID: group.id as number,
      }).unwrap();
      dispatch(
        showNotification(
          group.auto_accept_requests
            ? "Successfully joined group."
            : "Successfully requested admission to group.",
        ),
      );
    } catch {
      // error notification handled by the base query
    }
  };

  const handleDeleteAdmissionRequest = (admissionRequestID: number) => {
    deleteAdmissionRequest(admissionRequestID);
  };

  const renderActions = (params: any) => {
    const group = params.row;
    if (declinedRequestGroupIDs.includes(group.id)) {
      return <em>Admission request declined.</em>;
    }
    if (pendingRequestGroupIDs.includes(group.id)) {
      const admissionRequestID = groupAdmissionRequests?.filter(
        (request: any) => request.group_id === group.id,
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
        onClick={() => handleRequestAdmission(group)}
        data-testid={`requestAdmissionButton${group.id}`}
      >
        {group.auto_accept_requests ? "Join group" : "Request admission"}
      </Button>
    );
  };

  const columns: any[] = [
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
        getRowId={(row: any) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
        pageSizeOptions={[10, 25, 50, 100, 200]}
        showToolbar
      />
    </Box>
  );
};

export default NonMemberGroupList;

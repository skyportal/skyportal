import { useNavigate, Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import CircularProgress from "@mui/material/CircularProgress";
import DragHandleIcon from "@mui/icons-material/DragHandle";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useRequestGroupAdmissionMutation,
  useDeleteAdmissionRequestMutation,
} from "../../ducks/groupAdmissionRequests";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import { Group } from "../../types";

interface GroupListProps {
  title?: string;
  groups?: Group[];
  variant?: "normal" | "widget";
  linkToGroupSources?: boolean;
  admission?: boolean;
}

const GroupList = ({
  title,
  groups = [],
  variant = "normal",
  linkToGroupSources = false,
  admission = false,
}: GroupListProps) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [requestGroupAdmission] = useRequestGroupAdmissionMutation();
  const [deleteAdmissionRequest] = useDeleteAdmissionRequestMutation();
  const {
    id: currentUserID,
    streams: userStreams,
    permissions,
    groupAdmissionRequests,
  } = (useGetProfileQuery().data as any) ?? {};

  if (!groups?.length) return null;
  const multiUserGroups = groups.filter((group) => !group.single_user_group);

  const getLink = (group: Group) =>
    linkToGroupSources ? `/group_sources/${group.id}` : `/group/${group.id}`;

  if (variant === "widget") {
    return (
      <Paper sx={{ height: "100%" }}>
        <Box
          sx={{
            p: 2,
            height: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box>
            <DragHandleIcon
              className="dragHandle"
              sx={{ float: "right", color: "gray", m: 0.5, cursor: "pointer" }}
            />
            <Typography variant="h6">{title}</Typography>
          </Box>
          <List component="nav" sx={{ flex: 1, overflowY: "auto" }}>
            {multiUserGroups.map((group) => (
              <Link to={getLink(group)} key={group.id}>
                <ListItemButton data-testid={`${title}-${group.name}`}>
                  <ListItemText primary={group.name} />
                </ListItemButton>
              </Link>
            ))}
          </List>
        </Box>
      </Paper>
    );
  }

  if (admission && currentUserID == null) return <CircularProgress />;

  const pendingRequestGroupIDs = groupAdmissionRequests
    ?.filter((request: any) => request.status === "pending")
    ?.map((request: any) => request.group_id);
  const declinedRequestGroupIDs = groupAdmissionRequests
    ?.filter((request: any) => request.status === "declined")
    ?.map((request: any) => request.group_id);
  const isSystemAdmin = (permissions ?? []).includes("System admin");
  const userStreamIDs = new Set(
    (userStreams ?? []).map((stream: any) => stream.id),
  );

  const handleRequestAdmission = async (group: any) => {
    try {
      await requestGroupAdmission({
        userID: currentUserID,
        groupID: group.id,
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

  const renderAdmissionActions = (params: any) => {
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
            onClick={() => deleteAdmissionRequest(admissionRequestID)}
            data-testid={`deleteAdmissionRequestButton${group.id}`}
          >
            Delete request
          </Button>
        </>
      );
    }
    const label = group.auto_accept_requests
      ? "Join group"
      : "Request admission";
    const missingStreams = isSystemAdmin
      ? []
      : (group.streams ?? []).filter(
          (stream: any) => !userStreamIDs.has(stream.id),
        );
    if (missingStreams.length > 0) {
      const missingNames = missingStreams
        .map((stream: any) => stream.name)
        .join(", ");
      return (
        <Tooltip
          title={`You need access to the following stream(s) to join this group: ${missingNames}`}
        >
          <span>
            <Button
              secondary
              size="small"
              disabled
              data-testid={`requestAdmissionButton${group.id}`}
            >
              {label}
            </Button>
          </span>
        </Tooltip>
      );
    }
    return (
      <Button
        secondary
        size="small"
        onClick={() => handleRequestAdmission(group)}
        data-testid={`requestAdmissionButton${group.id}`}
      >
        {label}
      </Button>
    );
  };

  const columns = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 120 },
    { field: "nickname", headerName: "Nickname", flex: 1, minWidth: 120 },
    ...(admission
      ? [
          {
            field: "actions",
            headerName: "Actions",
            flex: 1,
            minWidth: 160,
            sortable: false,
            renderCell: renderAdmissionActions,
          },
        ]
      : []),
  ];

  return (
    <Box sx={{ width: "100%" }}>
      <StyledDataGrid
        autoHeight
        rows={multiUserGroups}
        columns={columns}
        getRowId={(row: any) => row.id}
        initialState={{ pagination: { paginationModel: { pageSize: 30 } } }}
        pageSizeOptions={[30, 50, 100, 200]}
        showToolbar
        onRowClick={
          admission ? undefined : (params: any) => navigate(getLink(params.row))
        }
        sx={admission ? {} : { "& .MuiDataGrid-row": { cursor: "pointer" } }}
      />
    </Box>
  );
};

export default GroupList;

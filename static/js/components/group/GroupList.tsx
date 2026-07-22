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
import IconButton from "@mui/material/IconButton";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useRequestGroupAdmissionMutation,
  useDeleteAdmissionRequestMutation,
} from "../../ducks/groupAdmissionRequests";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import { Group } from "../../types";

interface GroupListProps {
  title?: string;
  groups?: Group[];
  variant?: "normal" | "widget";
  linkToGroupSources?: boolean;
  admission?: boolean;
}

const GroupList = ({
  title = "",
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
    let label = group.auto_accept_requests ? "Join group" : "Request admission";
    let tooltip = "";
    let isDisable = false;
    let requestToDelete = null;

    if (declinedRequestGroupIDs.includes(group.id)) {
      tooltip = "This admission request has been declined.";
      label = "Admission request declined";
      isDisable = true;
    } else if (pendingRequestGroupIDs.includes(group.id)) {
      tooltip =
        "This admission is pending, you can delete this request by clicking on the cross";
      label = "Request pending...";
      isDisable = true;
      requestToDelete = groupAdmissionRequests?.filter(
        (request: any) => request.group_id === group.id,
      )[0]?.id;
    } else {
      const missingStreamNames = isSystemAdmin
        ? ""
        : (group.streams ?? [])
            .filter((stream: any) => !userStreamIDs.has(stream.id))
            .map((stream: any) => stream.name)
            .join(", ");
      if (missingStreamNames.length) {
        tooltip = `You need access to the following stream(s) to join this group: ${missingStreamNames}`;
        isDisable = true;
      }
    }
    return (
      <Tooltip title={tooltip}>
        <Box sx={{ display: "flex" }}>
          <Button
            secondary
            size="small"
            disabled={isDisable}
            onClick={() => handleRequestAdmission(group)}
            data-testid={`requestAdmissionButton${group.id}`}
          >
            {label}
          </Button>
          {requestToDelete !== null && (
            <IconButton
              color="error"
              size="small"
              onClick={() => deleteAdmissionRequest(requestToDelete)}
              data-testid={`deleteAdmissionRequestButton${group.id}`}
            >
              X
            </IconButton>
          )}
        </Box>
      </Tooltip>
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
      slots={{ toolbar: () => <DataGridToolbar title={title} /> }}
      sx={admission ? {} : { "& .MuiDataGrid-row": { cursor: "pointer" } }}
    />
  );
};

export default GroupList;

import { useState } from "react";
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
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

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

const GroupListToolbar = ({ title }: { title: string }) => (
  <DataGridToolbar title={title} />
);

interface GroupListProps {
  title?: string;
  groups?: Group[];
  variant?: "normal" | "widget";
  linkToGroupSources?: boolean;
  admission?: boolean;
  filterModel?: any;
  onFilterModelChange?: (model: any) => void;
}

const GroupList = ({
  title = "",
  groups = [],
  variant = "normal",
  linkToGroupSources = false,
  admission = false,
  filterModel,
  onFilterModelChange,
}: GroupListProps) => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [requestGroupAdmission, { isLoading: isRequesting }] =
    useRequestGroupAdmissionMutation();
  const [deleteAdmissionRequest] = useDeleteAdmissionRequestMutation();
  const [requestingGroup, setRequestingGroup] = useState<any>(null);
  const [reason, setReason] = useState("");
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

  const findRequest = (group: any, status: string) =>
    groupAdmissionRequests?.find(
      (request: any) =>
        request.group_id === group.id && request.status === status,
    );
  const isSystemAdmin = (permissions ?? []).includes("System admin");
  const userStreamIDs = new Set(
    (userStreams ?? []).map((stream: any) => stream.id),
  );

  const handleRequestAdmission = async (group: any, message?: string) => {
    const { error } = await requestGroupAdmission({
      userID: currentUserID,
      groupID: group.id,
      message,
    });
    if (error) return;
    dispatch(
      showNotification(
        group.auto_accept_requests
          ? "Successfully joined group."
          : "Successfully requested admission to group.",
      ),
    );
  };

  const renderAdmissionActions = (params: any) => {
    const group = params.row;
    let label = group.auto_accept_requests ? "Join group" : "Request admission";
    let tooltip = "";
    let isDisable = false;
    const declined = findRequest(group, "declined");
    const pendingRequest = !declined && findRequest(group, "pending");

    if (declined) {
      tooltip = "This admission request has been declined.";
      label = "Admission request declined";
      isDisable = true;
    } else if (pendingRequest) {
      tooltip =
        "This admission is pending, you can delete this request by clicking on the cross";
      label = "Request pending...";
      isDisable = true;
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
            disabled={isDisable || isRequesting}
            onClick={() => {
              if (group.auto_accept_requests) {
                handleRequestAdmission(group);
              } else {
                setReason("");
                setRequestingGroup(group);
              }
            }}
            data-testid={`requestAdmissionButton${group.id}`}
          >
            {label}
          </Button>
          {pendingRequest && (
            <IconButton
              color="error"
              size="small"
              onClick={() => deleteAdmissionRequest(pendingRequest.id)}
              data-testid={`deleteAdmissionRequestButton${group.id}`}
            >
              <CloseIcon />
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

  const closeRequestDialog = () => setRequestingGroup(null);

  const submitRequest = async () => {
    await handleRequestAdmission(requestingGroup, reason.trim());
    closeRequestDialog();
  };

  return (
    <>
      <StyledDataGrid
        autoHeight
        rows={multiUserGroups}
        columns={columns}
        filterModel={filterModel}
        onFilterModelChange={onFilterModelChange}
        showToolbar
        onRowClick={
          admission ? undefined : (params: any) => navigate(getLink(params.row))
        }
        slots={{ toolbar: GroupListToolbar }}
        slotProps={{ toolbar: { title } }}
        sx={admission ? {} : { "& .MuiDataGrid-row": { cursor: "pointer" } }}
      />
      <Dialog
        fullWidth
        maxWidth="sm"
        open={requestingGroup != null}
        onClose={closeRequestDialog}
      >
        <DialogTitle>Join {requestingGroup?.name}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label="Why do you want to join?"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            slotProps={{ htmlInput: { maxLength: 2000 } }}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button secondary onClick={closeRequestDialog}>
            Cancel
          </Button>
          <Button
            primary
            disabled={!reason.trim() || isRequesting}
            onClick={submitRequest}
            data-testid="submitAdmissionRequestButton"
          >
            Send request
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default GroupList;

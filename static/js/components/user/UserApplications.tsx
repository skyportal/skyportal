import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import { capitalize, userLabel } from "../../utils/format";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";
import {
  UserApplication,
  useDecideUserApplicationMutation,
  useDeleteUserApplicationMutation,
  useGetUserApplicationsQuery,
} from "../../ducks/userApplications";

const TABS: UserApplication["status"][] = ["pending", "endorsed", "declined"];

const STATUS_COLOR = {
  pending: "warning",
  endorsed: "success",
  declined: "error",
} as const;

const applicantName = (application: UserApplication) =>
  `${application.first_name} ${application.last_name}`;

const ApplicationsToolbar = () => (
  <DataGridToolbar title="Account applications" />
);

const groupStreams = (group: any): any[] => group?.streams ?? [];

const EndorseDialog = ({
  application,
  onClose,
}: {
  application: UserApplication;
  onClose: () => void;
}) => {
  const dispatch = useAppDispatch();
  const [decide] = useDecideUserApplicationMutation();
  const myStreams = useGetStreamsQuery().data ?? [];
  const myGroups = (useGetGroupsQuery().data?.user ?? []).filter(
    (group: any) => !group.single_user_group,
  );
  const [streamIDs, setStreamIDs] = useState<number[]>([]);
  const [groupIDs, setGroupIDs] = useState<number[]>([]);
  const [role, setRole] = useState<"Full user" | "View only">("Full user");

  // A group is only usable with the streams that feed its filters, so it can
  // be offered once the applicant is being given all of them.
  const availableGroups = myGroups.filter((group: any) =>
    groupStreams(group).every((stream: any) => streamIDs.includes(stream.id)),
  );

  const chooseStreams = (selected: number[]) => {
    setStreamIDs(selected);
    // Narrowing the streams can strand a group that was already picked.
    setGroupIDs((picked) =>
      picked.filter((id) =>
        groupStreams(myGroups.find((group: any) => group.id === id)).every(
          (stream: any) => selected.includes(stream.id),
        ),
      ),
    );
  };

  const endorse = async () => {
    const result = await decide({
      applicationID: application.id,
      payload: { status: "endorsed", streamIDs, groupIDs, role },
    });
    if ("error" in result) return;
    dispatch(
      showNotification(
        `Endorsed ${applicantName(application)}, and emailed an invitation to ${application.contact_email}.`,
      ),
    );
    onClose();
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{`Endorse ${applicantName(application)}?`}</DialogTitle>
      <DialogContent
        sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}
      >
        <DialogContentText>
          {`An invitation will be emailed to ${application.contact_email}. You can only grant streams you have yourself, and groups you belong to that those streams cover.`}
        </DialogContentText>
        {application.affiliation && (
          <Typography variant="body2">
            <b>Affiliation:</b> {application.affiliation}
          </Typography>
        )}
        {application.statement && (
          <Typography variant="body2">
            <b>Stated reason:</b> {application.statement}
          </Typography>
        )}
        <FormControl fullWidth>
          <InputLabel id="endorseRoleLabel">User role</InputLabel>
          <Select
            labelId="endorseRoleLabel"
            label="User role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            {["Full user", "View only"].map((option) => (
              <MenuItem key={option} value={option}>
                {option}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl fullWidth>
          <InputLabel id="endorseStreamsLabel">Streams</InputLabel>
          <Select
            multiple
            labelId="endorseStreamsLabel"
            label="Streams"
            value={streamIDs}
            onChange={(event) => chooseStreams(event.target.value as number[])}
            renderValue={(selected) =>
              myStreams
                .filter((stream: any) => selected.includes(stream.id))
                .map((stream: any) => stream.name)
                .join(", ")
            }
          >
            {myStreams.map((stream: any) => (
              <MenuItem key={stream.id} value={stream.id}>
                {stream.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl fullWidth>
          <InputLabel id="endorseGroupsLabel">Groups</InputLabel>
          <Select
            multiple
            labelId="endorseGroupsLabel"
            label="Groups"
            value={groupIDs}
            onChange={(event) => setGroupIDs(event.target.value as number[])}
            renderValue={(selected) =>
              myGroups
                .filter((group: any) => selected.includes(group.id))
                .map((group: any) => group.name)
                .join(", ")
            }
          >
            {availableGroups.map((group: any) => (
              <MenuItem key={group.id} value={group.id}>
                {group.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button primary onClick={endorse}>
          Endorse
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const DeclineDialog = ({
  application,
  onClose,
}: {
  application: UserApplication;
  onClose: () => void;
}) => {
  const dispatch = useAppDispatch();
  const [decide] = useDecideUserApplicationMutation();
  const [reason, setReason] = useState("");

  const decline = async () => {
    const result = await decide({
      applicationID: application.id,
      payload: { status: "declined", declineReason: reason || undefined },
    });
    if ("error" in result) return;
    dispatch(showNotification("Application declined."));
    onClose();
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{`Decline ${applicantName(application)}?`}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          The applicant is not notified. The reason is recorded for other
          endorsers.
        </DialogContentText>
        <TextField
          fullWidth
          multiline
          rows={3}
          margin="normal"
          label="Reason (optional)"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button secondary onClick={decline}>
          Decline
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const UserApplications = () => {
  const { canDecideUserApplications } = (useGetConfigQuery().data as any) ?? {};
  const [tabIndex, setTabIndex] = useState(0);
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: 25,
  });
  const status = TABS[tabIndex];
  const { data } = useGetUserApplicationsQuery(
    { status, ...fetchParams },
    { skip: !canDecideUserApplications },
  );
  const [deleteApplication] = useDeleteUserApplicationMutation();
  const [endorsing, setEndorsing] = useState<UserApplication | null>(null);
  const [declining, setDeclining] = useState<UserApplication | null>(null);

  if (canDecideUserApplications === false)
    return (
      <Typography variant="body2" color="textSecondary">
        You do not have permission to act on account applications, or they are
        not enabled on this instance.
      </Typography>
    );

  const applications = data?.applications ?? [];

  const columns = [
    {
      field: "applicant",
      headerName: "Applicant",
      flex: 1,
      minWidth: 160,
      sortable: false,
      valueGetter: (_value: any, row: UserApplication) => applicantName(row),
    },
    { field: "contact_email", headerName: "Email", flex: 1, minWidth: 180 },
    { field: "affiliation", headerName: "Affiliation", flex: 1, minWidth: 150 },
    {
      field: "endorser",
      headerName: "Endorser named",
      flex: 1,
      minWidth: 160,
      sortable: false,
      valueGetter: (_value: any, row: UserApplication) =>
        row.endorser
          ? userLabel(row.endorser, true)
          : (row.endorser_email ?? ""),
    },
    {
      field: "statement",
      headerName: "Stated reason",
      flex: 1.5,
      minWidth: 200,
      sortable: false,
      renderCell: ({ value }: { value?: string }) =>
        value ? (
          <Tooltip title={value}>
            <Typography variant="body2" noWrap>
              {value}
            </Typography>
          </Tooltip>
        ) : null,
    },
    {
      field: "created_at",
      headerName: "Applied",
      flex: 1,
      minWidth: 160,
      valueGetter: (value: string) =>
        (value ?? "").slice(0, 19).replace("T", " "),
    },
    {
      field: "status",
      headerName: "Status",
      flex: 0.6,
      minWidth: 110,
      renderCell: ({ row }: { row: UserApplication }) => (
        <Chip
          size="small"
          variant="outlined"
          label={capitalize(row.status)}
          color={STATUS_COLOR[row.status]}
        />
      ),
    },
    {
      field: "actions",
      headerName: " ",
      minWidth: 260,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: { row: UserApplication }) =>
        row.status === "endorsed" ? null : (
          <Box sx={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Button primary size="small" onClick={() => setEndorsing(row)}>
              Endorse
            </Button>
            {row.status === "pending" && (
              <Button secondary size="small" onClick={() => setDeclining(row)}>
                Decline
              </Button>
            )}
            <Button size="small" onClick={() => deleteApplication(row.id)}>
              Delete
            </Button>
          </Box>
        ),
    },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Tabs
        value={tabIndex}
        onChange={(_event, value) => {
          setTabIndex(value);
          setFetchParams({ ...fetchParams, pageNumber: 1 });
        }}
      >
        <Tab label="Pending" />
        <Tab label="Endorsed" />
        <Tab label="Declined" />
      </Tabs>
      {data && applications.length === 0 ? (
        <Typography variant="body2" color="textSecondary">
          {`No ${status} applications.`}
        </Typography>
      ) : (
        <StyledDataGrid
          autoHeight
          rows={applications}
          columns={columns}
          getRowId={(row: UserApplication) => row.id}
          paginationMode="server"
          rowCount={data?.totalMatches ?? 0}
          paginationModel={{
            page: fetchParams.pageNumber - 1,
            pageSize: fetchParams.numPerPage,
          }}
          onPaginationModelChange={(model: any) =>
            setFetchParams({
              pageNumber: model.page + 1,
              numPerPage: model.pageSize,
            })
          }
          pageSizeOptions={[25, 50, 100]}
          showToolbar
          slots={{ toolbar: ApplicationsToolbar }}
        />
      )}
      <Typography variant="body2" color="textSecondary">
        People applying for an account name an existing user to vouch for them.
        Endorsing one emails the applicant an invitation.
      </Typography>
      {endorsing && (
        <EndorseDialog
          application={endorsing}
          onClose={() => setEndorsing(null)}
        />
      )}
      {declining && (
        <DeclineDialog
          application={declining}
          onClose={() => setDeclining(null)}
        />
      )}
    </Box>
  );
};

export default UserApplications;

import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
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

type Decision = "endorsed" | "declined";
const TABS: UserApplication["status"][] = ["pending", "endorsed", "declined"];
const ROLES = ["Full user", "View only"] as const;

const applicantName = (application: UserApplication) =>
  `${application.first_name} ${application.last_name}`;

const endorserName = (application: UserApplication) =>
  application.endorser
    ? userLabel(application.endorser, true)
    : (application.endorser_email ?? "");

const formatDate = (value: string | null) =>
  (value ?? "").slice(0, 16).replace("T", " ");

const textCell = ({ value }: { value: string | null }) =>
  value ? (
    <Tooltip title={value}>
      <span>{value}</span>
    </Tooltip>
  ) : null;

const APPLICANT_COLUMNS = [
  {
    field: "applicant",
    headerName: "Applicant",
    flex: 1,
    minWidth: 150,
    sortable: false,
    valueGetter: (_value: any, row: UserApplication) => applicantName(row),
  },
  { field: "contact_email", headerName: "Email", flex: 1, minWidth: 180 },
  {
    field: "affiliation",
    headerName: "Affiliation",
    flex: 1,
    minWidth: 130,
    renderCell: textCell,
  },
];

const ENDORSER_COLUMN = {
  field: "endorser",
  headerName: "Endorser named",
  flex: 1,
  minWidth: 150,
  sortable: false,
  valueGetter: (_value: any, row: UserApplication) => endorserName(row),
};

const DECIDED_COLUMNS = [
  {
    field: "endorsed_by",
    headerName: "Decided by",
    flex: 1,
    minWidth: 150,
    sortable: false,
    valueGetter: (_value: any, row: UserApplication) =>
      row.endorsed_by ? userLabel(row.endorsed_by, true) : "",
  },
  {
    field: "decided_at",
    headerName: "Decided",
    flex: 1,
    minWidth: 140,
    valueGetter: formatDate,
  },
];

const COLUMNS_BY_STATUS = {
  pending: [
    ...APPLICANT_COLUMNS,
    ENDORSER_COLUMN,
    {
      field: "statement",
      headerName: "Stated reason",
      flex: 1.5,
      minWidth: 160,
      renderCell: textCell,
    },
    {
      field: "created_at",
      headerName: "Applied",
      flex: 1,
      minWidth: 120,
      valueGetter: formatDate,
    },
  ],
  endorsed: [...APPLICANT_COLUMNS, ENDORSER_COLUMN, ...DECIDED_COLUMNS],
  declined: [
    ...APPLICANT_COLUMNS,
    {
      field: "decline_reason",
      headerName: "Decline reason",
      flex: 1.5,
      minWidth: 170,
      renderCell: textCell,
    },
    ...DECIDED_COLUMNS,
  ],
};

const ACTIONS_WIDTH = { pending: 230, endorsed: 60, declined: 150 };

const groupStreams = (group: any): any[] => group?.streams ?? [];

const DecisionDialog = ({
  application,
  decision,
  onClose,
}: {
  application: UserApplication;
  decision: Decision;
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
  const [role, setRole] = useState<(typeof ROLES)[number]>("Full user");
  const [reason, setReason] = useState("");

  const endorsing = decision === "endorsed";
  const action = endorsing ? "Endorse" : "Decline";

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

  const submit = async () => {
    const result = await decide({
      applicationID: application.id,
      payload: endorsing
        ? { status: decision, streamIDs, groupIDs, role }
        : { status: decision, declineReason: reason || undefined },
    });
    if ("error" in result) return;
    dispatch(
      showNotification(
        endorsing
          ? `Endorsed ${applicantName(application)}, and emailed an invitation to ${application.contact_email}.`
          : "Application declined.",
      ),
    );
    onClose();
  };

  const summary = {
    Email: application.contact_email,
    Affiliation: application.affiliation,
    "Endorser named": endorserName(application),
    "Stated reason": application.statement,
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{`${action} ${applicantName(application)}?`}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              display: "flex",
              flexDirection: "column",
              gap: 0.5,
              backgroundColor: "action.hover",
            }}
          >
            {Object.entries(summary)
              .filter(([, value]) => value)
              .map(([label, value]) => (
                <Typography key={label} variant="body2">
                  <b>{`${label}: `}</b>
                  {value}
                </Typography>
              ))}
          </Paper>
          {endorsing ? (
            <>
              <FormControl fullWidth>
                <InputLabel id="endorseRoleLabel">User role</InputLabel>
                <Select
                  labelId="endorseRoleLabel"
                  label="User role"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                >
                  {ROLES.map((option) => (
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
                  onChange={(event) =>
                    chooseStreams(event.target.value as number[])
                  }
                  renderValue={(selected) => (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {myStreams
                        .filter((stream: any) => selected.includes(stream.id))
                        .map((stream: any) => (
                          <Chip
                            key={stream.id}
                            size="small"
                            label={stream.name}
                          />
                        ))}
                    </Box>
                  )}
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
                  onChange={(event) =>
                    setGroupIDs(event.target.value as number[])
                  }
                  renderValue={(selected) => (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {myGroups
                        .filter((group: any) => selected.includes(group.id))
                        .map((group: any) => (
                          <Chip
                            key={group.id}
                            size="small"
                            label={group.name}
                          />
                        ))}
                    </Box>
                  )}
                >
                  {availableGroups.map((group: any) => (
                    <MenuItem key={group.id} value={group.id}>
                      {group.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <DialogContentText variant="body2">
                {`An invitation will be emailed to ${application.contact_email}. You can only grant streams you have yourself, and groups you belong to that those streams cover.`}
              </DialogContentText>
            </>
          ) : (
            <>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Reason (optional)"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              <DialogContentText variant="body2">
                The applicant is not notified. The reason is recorded for other
                endorsers.
              </DialogContentText>
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button primary={endorsing} secondary={!endorsing} onClick={submit}>
          {action}
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
  const status = TABS[tabIndex] ?? "pending";
  const { data } = useGetUserApplicationsQuery(
    { status, ...fetchParams },
    { skip: !canDecideUserApplications },
  );
  const [deleteApplication] = useDeleteUserApplicationMutation();
  const [deciding, setDeciding] = useState<{
    application: UserApplication;
    decision: Decision;
  } | null>(null);
  const [deleting, setDeleting] = useState<UserApplication | null>(null);

  if (canDecideUserApplications === false)
    return (
      <Typography variant="body2" color="textSecondary">
        You do not have permission to act on account applications, or they are
        not enabled on this instance.
      </Typography>
    );

  const applications = data?.applications ?? [];

  const openDecision =
    (application: UserApplication, decision: Decision) => () =>
      setDeciding({ application, decision });

  const columns = [
    ...COLUMNS_BY_STATUS[status],
    {
      field: "actions",
      headerName: " ",
      minWidth: ACTIONS_WIDTH[status],
      sortable: false,
      filterable: false,
      disableExport: true,
      renderCell: ({ row }: { row: UserApplication }) => (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            height: "100%",
          }}
        >
          {row.status !== "endorsed" && (
            <Button
              primary
              size="small"
              onClick={openDecision(row, "endorsed")}
            >
              Endorse
            </Button>
          )}
          {row.status === "pending" && (
            <Button
              secondary
              size="small"
              onClick={openDecision(row, "declined")}
            >
              Decline
            </Button>
          )}
          <Tooltip title="Delete application">
            <IconButton
              size="small"
              color="error"
              onClick={() => setDeleting(row)}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box>
        <Typography variant="h5">Account applications</Typography>
        <Typography variant="body2" color="textSecondary">
          People applying for an account name an existing user to vouch for
          them. Endorsing one emails the applicant an invitation.
        </Typography>
      </Box>
      <Tabs
        value={tabIndex}
        onChange={(_event, value) => {
          setTabIndex(value);
          setFetchParams({ ...fetchParams, pageNumber: 1 });
        }}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        {TABS.map((tab) => (
          <Tab key={tab} label={capitalize(tab)} />
        ))}
      </Tabs>
      {data && applications.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center" }}>
          <Typography variant="body2" color="textSecondary">
            {`No ${status} applications.`}
          </Typography>
        </Paper>
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
          slots={{ toolbar: DataGridToolbar }}
        />
      )}
      {deciding && (
        <DecisionDialog
          application={deciding.application}
          decision={deciding.decision}
          onClose={() => setDeciding(null)}
        />
      )}
      <ConfirmDeletionDialog
        dialogOpen={Boolean(deleting)}
        closeDialog={() => setDeleting(null)}
        deleteFunction={() => {
          if (deleting) deleteApplication(deleting.id);
          setDeleting(null);
        }}
        resourceName={
          deleting ? `application from ${applicantName(deleting)}` : ""
        }
      />
    </Box>
  );
};

export default UserApplications;

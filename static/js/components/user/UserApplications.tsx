import { useState } from "react";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  UserApplication,
  useDecideUserApplicationMutation,
  useDeleteUserApplicationMutation,
  useGetUserApplicationsQuery,
} from "../../ducks/userApplications";

const useStyles = makeStyles()((theme) => ({
  section: { padding: theme.spacing(1) },
  actions: { display: "flex", alignItems: "center", gap: "0.5rem" },
  detail: { display: "flex", flexDirection: "column", gap: "1rem" },
}));

const TABS: ("pending" | "endorsed" | "declined")[] = [
  "pending",
  "endorsed",
  "declined",
];

const statusColor = (status: string) => {
  if (status === "endorsed") return "success";
  if (status === "pending") return "warning";
  return "error";
};

const applicantName = (application: UserApplication) =>
  `${application.first_name} ${application.last_name}`;

const userLabel = (user: UserApplication["endorser"]) =>
  user === null
    ? ""
    : user.first_name && user.last_name
      ? `${user.username} (${user.first_name} ${user.last_name})`
      : user.username;

/** Endorsement dialog: the groups and role the issued invitation carries. */
const EndorseDialog = ({
  application,
  onClose,
}: {
  application: UserApplication;
  onClose: () => void;
}) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [decide] = useDecideUserApplicationMutation();
  const myGroups = (useGetProfileQuery().data?.groups ?? []).filter(
    (group: any) => !group.single_user_group,
  );
  const [groupIDs, setGroupIDs] = useState<number[]>([]);
  const [role, setRole] = useState<"Full user" | "View only">("Full user");

  const endorse = async () => {
    try {
      await decide({
        applicationID: application.id,
        payload: { status: "endorsed", groupIDs, role },
      }).unwrap();
      dispatch(
        showNotification(
          `Endorsed ${applicantName(application)}; an invitation has been emailed to ${application.contact_email}.`,
        ),
      );
      onClose();
    } catch {
      // error notification handled by the base query
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{`Endorse ${applicantName(application)}?`}</DialogTitle>
      <DialogContent className={classes.detail}>
        <DialogContentText>
          {`An invitation will be emailed to ${application.contact_email}. You can only add them to groups you belong to.`}
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
            onChange={(event) => setRole(event.target.value as any)}
            data-testid="endorseRoleSelect"
          >
            {["Full user", "View only"].map((option) => (
              <MenuItem key={option} value={option}>
                {option}
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
            data-testid="endorseGroupsSelect"
          >
            {myGroups.map((group: any) => (
              <MenuItem key={group.id} value={group.id}>
                {group.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button primary onClick={endorse} data-testid="confirmEndorseButton">
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
    try {
      await decide({
        applicationID: application.id,
        payload: { status: "declined", declineReason: reason || undefined },
      }).unwrap();
      dispatch(showNotification("Application declined."));
      onClose();
    } catch {
      // error notification handled by the base query
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{`Decline ${applicantName(application)}?`}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          The applicant is not notified; the reason is recorded for other
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
          data-testid="declineReasonInput"
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button secondary onClick={decline} data-testid="confirmDeclineButton">
          Decline
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const UserApplications = () => {
  const { classes } = useStyles();
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

  const applications = data?.applications ?? [];

  const renderActions = (params: any) => {
    const application = params.row as UserApplication;
    return (
      <div className={classes.actions}>
        {application.status !== "endorsed" && (
          <Button
            primary
            size="small"
            onClick={() => setEndorsing(application)}
            data-testid={`endorseButton${application.id}`}
          >
            Endorse
          </Button>
        )}
        {application.status === "pending" && (
          <Button
            secondary
            size="small"
            onClick={() => setDeclining(application)}
            data-testid={`declineApplicationButton${application.id}`}
          >
            Decline
          </Button>
        )}
        {application.status !== "endorsed" && (
          <Button
            size="small"
            onClick={() => deleteApplication(application.id)}
            data-testid={`deleteApplicationButton${application.id}`}
          >
            Delete
          </Button>
        )}
      </div>
    );
  };

  const columns: any[] = [
    {
      field: "applicant",
      headerName: "Applicant",
      flex: 1,
      minWidth: 160,
      sortable: false,
      valueGetter: (_value: any, row: any) => applicantName(row),
    },
    { field: "contact_email", headerName: "Email", flex: 1, minWidth: 180 },
    { field: "affiliation", headerName: "Affiliation", flex: 1, minWidth: 150 },
    {
      field: "endorser",
      headerName: "Endorser named",
      flex: 1,
      minWidth: 160,
      sortable: false,
      valueGetter: (_value: any, row: any) =>
        userLabel(row.endorser) || row.endorser_email || "—",
    },
    {
      field: "statement",
      headerName: "Stated reason",
      flex: 1.5,
      minWidth: 200,
      sortable: false,
    },
    { field: "created_at", headerName: "Applied", flex: 1, minWidth: 170 },
    {
      field: "status",
      headerName: "Status",
      flex: 0.6,
      minWidth: 110,
      renderCell: (params: any) => (
        <Chip
          size="small"
          variant="outlined"
          label={params.row.status}
          color={statusColor(params.row.status) as any}
        />
      ),
    },
    {
      field: "actions",
      headerName: " ",
      minWidth: 260,
      sortable: false,
      filterable: false,
      renderCell: renderActions,
    },
  ];

  if (canDecideUserApplications === false) {
    return (
      <Typography variant="body2" color="textSecondary">
        You do not have permission to act on account applications, or they are
        not enabled on this instance.
      </Typography>
    );
  }

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Typography variant="h5">Account applications</Typography>
        <Typography variant="body2" color="textSecondary">
          People applying for an account name an existing user to vouch for
          them. Endorsing one emails the applicant an invitation.
        </Typography>
        <Tabs
          value={tabIndex}
          onChange={(_event, value) => {
            setTabIndex(value);
            setFetchParams({ ...fetchParams, pageNumber: 1 });
          }}
          centered
        >
          <Tab label="Pending" />
          <Tab label="Endorsed" />
          <Tab label="Declined" />
        </Tabs>
        <Paper className={classes.section}>
          {data && applications.length === 0 ? (
            <Typography variant="body2" color="textSecondary">
              {`No ${status} applications.`}
            </Typography>
          ) : (
            <StyledDataGrid
              autoHeight
              rows={applications}
              columns={columns}
              getRowId={(row: any) => row.id}
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
            />
          )}
        </Paper>
      </Grid>
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
    </Grid>
  );
};

export default UserApplications;

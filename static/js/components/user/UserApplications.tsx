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
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import { capitalize, userLabel } from "../../utils/format";
import { Group } from "../../types/domain";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  UserApplication,
  useDecideUserApplicationMutation,
  useDeleteUserApplicationMutation,
  useGetUserApplicationsQuery,
} from "../../ducks/userApplications";

type Decision = "endorsed" | "declined";
const TABS: UserApplication["status"][] = ["pending", "endorsed", "declined"];
const ROLES = ["Full user", "View only"] as const;

const STATUS_COLOR = {
  pending: "warning",
  endorsed: "success",
  declined: "error",
} as const;

const applicantName = (application: UserApplication) =>
  `${application.first_name} ${application.last_name}`;

const COLUMNS = [
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
      row.endorser ? userLabel(row.endorser, true) : (row.endorser_email ?? ""),
  },
  { field: "statement", headerName: "Stated reason", flex: 1.5, minWidth: 200 },
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
];

const ApplicationsToolbar = () => (
  <DataGridToolbar title="Account applications" />
);

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
  const myGroups: Group[] = (useGetProfileQuery().data?.groups ?? []).filter(
    (group: Group) => !group.single_user_group,
  );
  const [groupIDs, setGroupIDs] = useState<number[]>([]);
  const [role, setRole] = useState<(typeof ROLES)[number]>("Full user");
  const [reason, setReason] = useState("");

  const endorsing = decision === "endorsed";
  const action = endorsing ? "Endorse" : "Decline";

  const submit = async () => {
    const result = await decide({
      applicationID: application.id,
      payload: endorsing
        ? { status: decision, groupIDs, role }
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

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{`${action} ${applicantName(application)}?`}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {endorsing ? (
          <>
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
              <InputLabel id="endorseGroupsLabel">Groups</InputLabel>
              <Select
                multiple
                labelId="endorseGroupsLabel"
                label="Groups"
                value={groupIDs}
                onChange={(event) =>
                  setGroupIDs(event.target.value as number[])
                }
                renderValue={(selected) =>
                  myGroups
                    .filter((group) => selected.includes(group.id))
                    .map((group) => group.name)
                    .join(", ")
                }
              >
                {myGroups.map((group) => (
                  <MenuItem key={group.id} value={group.id}>
                    {group.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </>
        ) : (
          <>
            <DialogContentText>
              The applicant is not notified. The reason is recorded for other
              endorsers.
            </DialogContentText>
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Reason (optional)"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </>
        )}
      </DialogContent>
      <DialogActions>
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
  const status = TABS[tabIndex];
  const { data } = useGetUserApplicationsQuery(
    { status, ...fetchParams },
    { skip: !canDecideUserApplications },
  );
  const [deleteApplication] = useDeleteUserApplicationMutation();
  const [deciding, setDeciding] = useState<{
    application: UserApplication;
    decision: Decision;
  } | null>(null);

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
    ...COLUMNS,
    {
      field: "actions",
      headerName: " ",
      minWidth: 260,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: { row: UserApplication }) =>
        row.status === "endorsed" ? null : (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Button
              primary
              size="small"
              onClick={openDecision(row, "endorsed")}
            >
              Endorse
            </Button>
            {row.status === "pending" && (
              <Button
                secondary
                size="small"
                onClick={openDecision(row, "declined")}
              >
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
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Tabs
        value={tabIndex}
        onChange={(_event, value) => {
          setTabIndex(value);
          setFetchParams({ ...fetchParams, pageNumber: 1 });
        }}
      >
        {TABS.map((tab) => (
          <Tab key={tab} label={capitalize(tab)} />
        ))}
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
      {deciding && (
        <DecisionDialog
          application={deciding.application}
          decision={deciding.decision}
          onClose={() => setDeciding(null)}
        />
      )}
    </Box>
  );
};

export default UserApplications;

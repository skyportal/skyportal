import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import TextareaAutosize from "@mui/material/TextareaAutosize";
import Box from "@mui/material/Box";
import Autocomplete from "@mui/material/Autocomplete";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import EditIcon from "@mui/icons-material/Edit";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import FilterListIcon from "@mui/icons-material/FilterList";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import Tooltip from "@mui/material/Tooltip";
import HelpIcon from "@mui/icons-material/Help";
import { makeStyles } from "tss-react/mui";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarExport,
} from "@mui/x-data-grid";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import PapaParse from "papaparse";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import FormValidationError from "../FormValidationError";
import { useGetGroupsQuery } from "../../ducks/groups";
import {
  useGetInvitationsQuery,
  useInviteUserMutation,
  useUpdateInvitationMutation,
  useDeleteInvitationMutation,
} from "../../ducks/invitations";
import { useGetStreamsQuery } from "../../ducks/streams";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import Spinner from "../Spinner";
import { useAppDispatch } from "../../types/hooks";

dayjs.extend(utc);

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200];

const useStyles = makeStyles()(() => ({
  icon: {
    height: "1rem",
  },
  headerCell: {
    verticalAlign: "bottom",
  },
  container: { padding: "1rem" },
  section: { margin: "0.5rem 0 1rem 0" },
  spinnerDiv: {
    paddingTop: "2rem",
  },
  submitButton: {
    marginTop: "1rem",
  },
  expired_user: {
    color: "red",
  },
}));

const sampleCSVText = `example1@gmail.com,1,3,false
example2@gmail.com,1 2 3,2 5 9,false false true`;

const defaultNumPerPage = 25;

const UserInvitations = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const { data: streams } = useGetStreamsQuery();
  let allGroups = useGetGroupsQuery().data?.all ?? null;
  const [rowsPerPage, setRowsPerPage] = useState(defaultNumPerPage);
  const [queryInProgress, setQueryInProgress] = useState(false);
  const { data: currentUser } = useGetProfileQuery();
  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });
  const [tableFilterList, setTableFilterList] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const { data: invitationsData } = useGetInvitationsQuery(fetchParams);
  const invitations = invitationsData?.invitations;
  const totalMatches = invitationsData?.totalMatches ?? 0;
  const [inviteUser] = useInviteUserMutation();
  const [updateInvitation] = useUpdateInvitationMutation();
  const [deleteInvitation] = useDeleteInvitationMutation();
  const [csvData, setCsvData] = useState("");
  const [addInvitationGroupsDialogOpen, setAddInvitationGroupsDialogOpen] =
    useState(false);
  const [addInvitationStreamsDialogOpen, setAddInvitationStreamsDialogOpen] =
    useState(false);
  const [updateRoleDialogOpen, setUpdateRoleDialogOpen] = useState(false);
  const [
    editUserExpirationDateDialogOpen,
    setEditUserExpirationDateDialogOpen,
  ] = useState(false);
  const [clickedInvitation, setClickedInvitation] = useState<any>(null);
  const [deleteInvitationDialogOpen, setDeleteInvitationDialogOpen] =
    useState(false);

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  if (!allGroups?.length || streams == null) {
    return (
      <Box
        display={queryInProgress ? "block" : "none"}
        className={classes.spinnerDiv}
      >
        <Spinner />
      </Box>
    );
  }

  if (
    !(
      currentUser?.permissions?.includes("System admin") ||
      currentUser?.permissions?.includes("Manage users")
    )
  ) {
    return <div>Access denied: Insufficient permissions.</div>;
  }
  allGroups = allGroups?.filter((group) => !group["single_user_group"]);

  const validateInvitationGroups = () => {
    const formState = getValues();
    return formState["invitationGroups"].length >= 1;
  };

  const validateInvitationStreams = () => {
    const formState = getValues();
    return formState["invitationStreams"].length >= 1;
  };

  const handleClickDeleteInvitationGroup = async (
    invitation: any,
    groupID: any,
  ) => {
    const groupIDs = invitation.groups
      ?.filter((group: any) => group.id !== groupID)
      ?.map((g: any) => g.id);
    try {
      await updateInvitation({
        invitationID: invitation.id,
        payload: { groupIDs },
      }).unwrap();
      dispatch(showNotification("Invitation successfully updated."));
    } catch {
      // error notification handled by the base query
    }
  };

  const handleClickDeleteInvitationStream = async (
    invitation: any,
    streamID: any,
  ) => {
    const streamIDs = invitation.streams
      ?.filter((stream: any) => stream.id !== streamID)
      ?.map((s: any) => s.id);
    try {
      await updateInvitation({
        invitationID: invitation.id,
        payload: { streamIDs },
      }).unwrap();
      dispatch(showNotification("Invitation successfully updated."));
    } catch {
      // error notification handled by the base query
    }
  };

  const handleAddInvitationGroups = async (formData: any) => {
    const groupIDs = new Set([
      ...clickedInvitation.groups?.map((g: any) => g.id),
      ...formData.invitationGroups?.map((g: any) => g.id),
    ]);

    try {
      await updateInvitation({
        invitationID: clickedInvitation.id,
        payload: { groupIDs: [...groupIDs] },
      }).unwrap();
      dispatch(showNotification("Invitation successfully updated."));
      reset({ invitationGroups: [] });
      setAddInvitationGroupsDialogOpen(false);
      setClickedInvitation(null);
    } catch {
      // error notification handled by the base query
    }
  };

  const handleAddInvitationStreams = async (formData: any) => {
    const streamIDs = new Set([
      ...clickedInvitation.streams?.map((s: any) => s.id),
      ...formData.invitationStreams?.map((s: any) => s.id),
    ]);

    try {
      await updateInvitation({
        invitationID: clickedInvitation.id,
        payload: { streamIDs: [...streamIDs] },
      }).unwrap();
      dispatch(showNotification("Invitation successfully updated."));
      reset({ invitationStreams: [] });
      setAddInvitationStreamsDialogOpen(false);
      setClickedInvitation(null);
    } catch {
      // error notification handled by the base query
    }
  };

  const handleUpdateInvitationRole = async (formData: any) => {
    try {
      await updateInvitation({
        invitationID: clickedInvitation.id,
        payload: { role: formData.invitationRole },
      }).unwrap();
      dispatch(showNotification("Invitation successfully updated."));
      reset({ invitationRole: "" });
      setUpdateRoleDialogOpen(false);
      setClickedInvitation(null);
    } catch {
      // error notification handled by the base query
    }
  };

  const handleDeleteInvitation = async (invitationID: any) => {
    try {
      await deleteInvitation(invitationID).unwrap();
      dispatch(showNotification("Invitation successfully deleted."));
    } catch {
      // error notification handled by the base query
    }
  };

  const handleClickAddUsers = async () => {
    let rows = PapaParse.parse(csvData.trim(), {
      delimiter: ",",
      skipEmptyLines: "greedy",
    }).data as any[];
    rows = rows.map((row: any) => [
      row[0].trim(),
      PapaParse.parse(row[1].trim(), { delimiter: " " }).data[0],
      PapaParse.parse(row[2].trim(), { delimiter: " " }).data[0],
      PapaParse.parse(row[3].trim(), {
        delimiter: " ",
        dynamicTyping: true,
        quotes: false,
      } as any).data[0],
      row[4]?.trim(),
    ]);
    const promises = rows.map((row: any) =>
      inviteUser({
        userEmail: row[0],
        streamIDs: row[1],
        groupIDs: row[2],
        groupAdmin: row[3],
        userExpirationDate: row[4],
      }).unwrap(),
    );
    try {
      await Promise.all(promises);
      dispatch(showNotification("User(s) invitation(s) successfully created."));
      setCsvData("");
    } catch {
      // error notification handled by the base query
    }
  };

  const handleEditUserExpirationDate = async (formData: any) => {
    if (!dayjs.utc(formData.date).isValid()) {
      dispatch(
        showNotification(
          "Invalid date. Please use MM/DD/YYYY format.",
          "error",
        ),
      );
      return;
    }
    try {
      await updateInvitation({
        invitationID: clickedInvitation.id,
        payload: {
          userExpirationDate: dayjs.utc(formData.date).toISOString(),
        },
      }).unwrap();
      dispatch(showNotification("User expiration date successfully updated."));
      reset({ date: null });
      setEditUserExpirationDateDialogOpen(false);
      setClickedInvitation(null);
    } catch {
      // error notification handled by the base query
    }
  };

  // DataGrid cell renderers
  const renderActions = (params: any) => {
    const invitation = params.row;
    const handleCopyInvitationLink = () => {
      const appBaseUrl = `${window.location.protocol}//${window.location.host}`;
      const invitationLink = `${appBaseUrl}/login/google-oauth2/?invite_token=${invitation.token}`;
      navigator.clipboard.writeText(invitationLink);
      dispatch(
        showNotification(
          `Invitation link for ${invitation.user_email} copied to clipboard.`,
          "info",
        ),
      );
    };
    return (
      <div>
        <Tooltip title="Copy invitation link to clipboard">
          <IconButton
            aria-label="copy-invitation-link"
            data-testid={`copyInvitationLink_${invitation.user_email}`}
            onClick={handleCopyInvitationLink}
            size="small"
          >
            <ContentCopyIcon />
          </IconButton>
        </Tooltip>
        <IconButton
          aria-label="delete-invitation"
          data-testid={`deleteInvitation_${invitation.user_email}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setDeleteInvitationDialogOpen(true);
          }}
          size="small"
        >
          <DeleteIcon />
        </IconButton>
      </div>
    );
  };

  const renderRole = (params: any) => {
    const invitation = params.row;
    return (
      <div>
        {invitation.role_id}
        &nbsp;
        <IconButton
          aria-label="edit-invitation-role"
          data-testid={`editInvitationRoleButton${invitation.user_email}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setUpdateRoleDialogOpen(true);
          }}
          size="small"
        >
          <EditIcon color="disabled" />
        </IconButton>
      </div>
    );
  };

  const renderGroups = (params: any) => {
    const invitation = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-invitation-groups"
          data-testid={`addInvitationGroupsButton${invitation.id}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setAddInvitationGroupsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {invitation.groups?.map((group: any) => (
          <Chip
            label={group.name}
            onDelete={() => {
              handleClickDeleteInvitationGroup(invitation, group.id);
            }}
            key={group.id}
            id={`invitationGroupChip_${invitation.id}_${group.id}`}
          />
        ))}
      </div>
    );
  };

  const renderStreams = (params: any) => {
    const invitation = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-invitation-streams"
          data-testid={`addInvitationStreamsButton${invitation.user_email}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setAddInvitationStreamsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {invitation.streams?.map((stream: any) => (
          <Chip
            label={stream.name}
            onDelete={() => {
              handleClickDeleteInvitationStream(invitation, stream.id);
            }}
            key={stream.id}
            id={`invitationStreamChip_${invitation.id}_${stream.id}`}
          />
        ))}
      </div>
    );
  };

  const renderExpirationDate = (params: any) => {
    const invitation = params.row;
    const isExpired = dayjs.utc().isAfter(invitation.user_expiration_date);
    return (
      <div className={isExpired ? classes.expired_user : ""}>
        {invitation.user_expiration_date
          ? dayjs.utc(invitation.user_expiration_date).format("YYYY/MM/DD")
          : ""}
        <IconButton
          aria-label="edit-expiration"
          data-testid={`editUserExpirationDate${invitation.id}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setEditUserExpirationDateDialogOpen(true);
          }}
          size="small"
        >
          <EditIcon color="disabled" />
        </IconButton>
      </div>
    );
  };

  const renderExpirationDateHeader = () => (
    <div style={{ display: "flex", alignItems: "center" }}>
      Expiration Date
      <Tooltip
        title={
          <>
            This is the expiration date assigned to the new user account. On
            this date, the user account will be deactivated and will be unable
            to access the application.
          </>
        }
      >
        <HelpIcon color="disabled" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const handleFilterSubmit = (formData: any) => {
    setQueryInProgress(true);
    Object.keys(formData).forEach(
      (key) => !formData[key] && delete formData[key],
    );
    setTableFilterList(
      Object.entries(formData).map(([key, value]) => `${key}: ${value}`),
    );
    const params = {
      pageNumber: 1,
      numPerPage: fetchParams.numPerPage,
      ...formData,
    };
    setFetchParams(params);
    setQueryInProgress(false);
    setFilterOpen(false);
  };

  const handleFilterChipDelete = (chip: string) => {
    const remaining = tableFilterList.filter((c) => c !== chip);
    const data: any = {};
    remaining.forEach((filterChip) => {
      const [key, value] = filterChip.split(": ");
      if (key) {
        data[key] = value;
      }
    });
    handleFilterSubmit(data);
  };

  const handlePageChange = (page: number, numPerPage: number) => {
    setQueryInProgress(true);
    const params = { ...fetchParams, numPerPage, pageNumber: page + 1 };
    // Save state for future
    setFetchParams(params);
    setQueryInProgress(false);
  };

  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    handlePageChange(model.page, model.pageSize);
  };

  const customFilterDisplay = () => {
    // Assemble json form schema for possible server-side filtering values
    const filterFormSchema = {
      type: "object",
      properties: {
        email: {
          type: "string",
          title: "Email",
        },
        group: {
          title: "Group",
          type: "string",
          enum: allGroups?.map((group) => group.name),
        },
        stream: {
          title: "Stream",
          type: "string",
          enum: streams?.map((stream: any) => stream.name),
        },
        invitedBy: {
          type: "string",
          title: "Invited by",
        },
      },
    };

    return !queryInProgress ? (
      <div>
        <Form
          schema={filterFormSchema as any}
          validator={validator}
          onSubmit={
            (({ formData }: { formData: any }) => {
              handleFilterSubmit(formData);
            }) as any
          }
        />
      </div>
    ) : (
      <div />
    );
  };

  const columns: any[] = [
    {
      field: "user_email",
      headerName: "Invitee Email",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.user_email,
    },
    {
      field: "role",
      headerName: "Role",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderRole,
    },
    {
      field: "groups",
      headerName: "Groups",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderGroups,
    },
    {
      field: "streams",
      headerName: "Streams",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderStreams,
    },
    {
      field: "invited_by",
      headerName: "Invited By",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      valueGetter: (_value: any, row: any) => row.invited_by?.username,
    },
    {
      field: "user_expiration_date",
      headerName: "User Expiration Date",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      renderHeader: renderExpirationDateHeader,
      renderCell: renderExpirationDate,
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderActions,
    },
  ];

  const CustomToolbar = function UserInvitationsToolbar() {
    return (
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <GridToolbarExport />
        <Tooltip title="Filter Table">
          <IconButton
            size="small"
            data-testid="Filter Table-iconButton"
            onClick={() => setFilterOpen(true)}
          >
            <FilterListIcon />
          </IconButton>
        </Tooltip>
        {tableFilterList.map((chip) => (
          <Chip
            key={chip}
            label={chip}
            size="small"
            onDelete={() => handleFilterChipDelete(chip)}
          />
        ))}
      </GridToolbarContainer>
    );
  };

  return (
    <>
      <Typography variant="h5">Pending Invitations</Typography>
      <Paper
        variant="outlined"
        className={classes.section}
        data-testid="pendingInvitations"
      >
        <Box sx={{ width: "100%" }}>
          <StyledDataGrid
            autoHeight
            columns={columns}
            rows={invitations || []}
            getRowId={(row: any) => row.id}
            loading={queryInProgress}
            paginationMode="server"
            sortingMode="server"
            rowCount={totalMatches}
            paginationModel={{
              page: fetchParams.pageNumber - 1,
              pageSize: rowsPerPage,
            }}
            onPaginationModelChange={handlePaginationModelChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            disableColumnFilter
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
      </Paper>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>{customFilterDisplay()}</DialogContent>
      </Dialog>
      <Typography variant="h5">Bulk Invite New Users</Typography>
      <Paper variant="outlined" className={classes.section}>
        <Box p={5}>
          <code>
            User Email,Stream IDs,Group IDs,true/false indicating admin status
            for respective groups, User expiration date (list values
            space-separated, no spaces after commas)
          </code>
          <br />
          <TextareaAutosize
            placeholder={sampleCSVText}
            name="bulkInviteCSVInput"
            style={{ height: "15rem", width: "50rem" }}
            onChange={(e) => {
              setCsvData(e.target.value);
            }}
            value={csvData}
          />
        </Box>
        <Box pl={5} pb={5}>
          <Button
            secondary
            data-testid="bulkAddUsersButton"
            onClick={handleClickAddUsers}
          >
            Add Users
          </Button>
        </Box>
      </Paper>
      <Dialog
        open={addInvitationGroupsDialogOpen}
        onClose={() => setAddInvitationGroupsDialogOpen(false)}
      >
        <DialogTitle>
          {`Add selected groups to invitation for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddInvitationGroups)}>
            {!!errors["invitationGroups"] && (
              <FormValidationError message="Please select at least one group" />
            )}
            <Controller
              name="invitationGroups"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  value={value}
                  onChange={(_e, data) => onChange(data)}
                  options={allGroups?.filter(
                    (group) =>
                      !clickedInvitation?.groups
                        ?.map((g: any) => g.id)
                        ?.includes(group.id),
                  )}
                  getOptionLabel={(group: any) => group.name}
                  filterSelectedOptions
                  data-testid="addInvitationGroupsSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      error={!!errors["invitationGroups"]}
                      variant="outlined"
                      label="Select Groups"
                      data-testid="addInvitationGroupsTextField"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateInvitationGroups }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddInvitationGroupsButton"
                data-testid="submitAddInvitationGroupsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={addInvitationStreamsDialogOpen}
        onClose={() => setAddInvitationStreamsDialogOpen(false)}
      >
        <DialogTitle>
          {`Add selected streams to invitation for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddInvitationStreams)}>
            {!!errors["invitationStreams"] && (
              <FormValidationError message="Please select at least one stream" />
            )}
            <Controller
              name="invitationStreams"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  value={value}
                  onChange={(_e, data) => onChange(data)}
                  options={streams?.filter(
                    (stream: any) =>
                      !clickedInvitation?.streams
                        ?.map((s: any) => s.id)
                        ?.includes(stream.id),
                  )}
                  getOptionLabel={(stream: any) => stream.name}
                  filterSelectedOptions
                  data-testid="addInvitationStreamsSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      error={!!errors["invitationStreams"]}
                      variant="outlined"
                      label="Select Streams"
                      data-testid="addInvitationStreamsTextField"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateInvitationStreams }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddInvitationStreamsButton"
                data-testid="submitAddInvitationStreamsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={updateRoleDialogOpen}
        onClose={() => setUpdateRoleDialogOpen(false)}
      >
        <DialogTitle>
          {`Edit user role for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleUpdateInvitationRole)}>
            {!!errors["invitationRole"] && (
              <FormValidationError message="Please select one role" />
            )}
            <Controller
              name="invitationRole"
              control={control}
              rules={{ required: true }}
              defaultValue={clickedInvitation?.role_id}
              render={({ field: { onChange, value } }) => (
                <Select
                  data-testid="invitationRoleSelect"
                  value={value}
                  onChange={onChange}
                >
                  {["Full user", "View only"].map((role) => (
                    <MenuItem key={role} value={role}>
                      {role}
                    </MenuItem>
                  ))}
                </Select>
              )}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitEditRoleButton"
                data-testid="submitEditRoleButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={editUserExpirationDateDialogOpen}
        onClose={() => setEditUserExpirationDateDialogOpen(false)}
      >
        <DialogTitle>Edit user expiration date:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleEditUserExpirationDate)}>
            <Controller
              render={({ field: { onChange, value } }) => (
                <DatePicker
                  value={value}
                  onChange={(newValue) => onChange(newValue)}
                  slotProps={{ textField: { variant: "outlined" } }}
                  label="Expiration date (UTC)"
                  {...({ showTodayButton: false } as any)}
                />
              )}
              name="date"
              control={control}
              defaultValue={null}
            />
            <br />
            <div className={classes.submitButton}>
              <Button
                primary
                type="submit"
                name="submitExpirationDateButton"
                data-testid="submitExpirationDateButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        dialogOpen={deleteInvitationDialogOpen}
        closeDialog={() => setDeleteInvitationDialogOpen(false)}
        deleteFunction={() => {
          handleDeleteInvitation(clickedInvitation.id);
          setDeleteInvitationDialogOpen(false);
        }}
        resourceName={`invitation for ${clickedInvitation?.user_email}`}
      />
    </>
  );
};

export default UserInvitations;

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
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import PapaParse from "papaparse";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import FormValidationError from "../FormValidationError";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";
import {
  useGetInvitationsQuery,
  useInviteUserMutation,
  useUpdateInvitationMutation,
  useDeleteInvitationMutation,
} from "../../ducks/invitations";
import { useAppDispatch } from "../../types/hooks";

dayjs.extend(utc);

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200];
const DEFAULT_NUM_PER_PAGE = 25;

const SAMPLE_CSV_TEXT = `example1@gmail.com,1,3,false
example2@gmail.com,1 2 3,2 5 9,false false true`;

const ENTITIES = {
  Groups: { field: "groups", payloadKey: "groupIDs", singular: "Group" },
  Streams: { field: "streams", payloadKey: "streamIDs", singular: "Stream" },
} as const;

type EntityKind = keyof typeof ENTITIES;

const cellSx = {
  display: "flex",
  alignItems: "center",
  gap: 0.5,
  flexWrap: "wrap",
  "& .MuiChip-deleteIcon": { display: "none" },
  "& .MuiChip-root:hover .MuiChip-deleteIcon": { display: "inline-block" },
} as const;

const chipCellSx = {
  ...cellSx,
  "& > .MuiIconButton-root": { display: "none" },
  ".MuiDataGrid-cell:hover & > .MuiIconButton-root": { display: "inline-flex" },
} as const;

const renderExpirationDateHeader = () => (
  <Box sx={{ display: "flex", alignItems: "center" }}>
    Expiration Date
    <Tooltip title="This is the expiration date assigned to the new user account. On this date, the user account will be deactivated and will be unable to access the application.">
      <HelpIcon color="disabled" sx={{ height: "1rem" }} />
    </Tooltip>
  </Box>
);

const InvitationsToolbar = ({
  filters,
  onOpenFilters,
  onDeleteFilter,
}: any) => (
  <DataGridToolbar title="Pending Invitations" showQuickFilter={false}>
    <Tooltip title="Filter Table">
      <IconButton size="small" onClick={onOpenFilters}>
        <FilterListIcon />
      </IconButton>
    </Tooltip>
    {filters.map((chip: string) => (
      <Chip
        key={chip}
        label={chip}
        size="small"
        onDelete={() => onDeleteFilter(chip)}
      />
    ))}
  </DataGridToolbar>
);

const AddEntitiesDialog = ({
  kind,
  open,
  onClose,
  email,
  options,
  control,
  error,
  onSubmit,
}: any) => {
  const singular = ENTITIES[kind as EntityKind].singular.toLowerCase();
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>
        {`Add selected ${singular}s to invitation for ${email}:`}
      </DialogTitle>
      <DialogContent>
        <Box
          component="form"
          onSubmit={onSubmit}
          sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
        >
          {error && (
            <FormValidationError
              message={`Please select at least one ${singular}`}
            />
          )}
          <Controller
            name={`invitation${kind}`}
            control={control}
            rules={{ validate: (value: any) => value.length >= 1 }}
            defaultValue={[]}
            render={({ field: { onChange, value } }) => (
              <Autocomplete
                multiple
                value={value}
                onChange={(_e, data) => onChange(data)}
                options={options}
                getOptionLabel={(entity: any) => entity.name}
                filterSelectedOptions
                data-testid={`addInvitation${kind}Select`}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    error={error}
                    variant="outlined"
                    label={`Select ${kind}`}
                  />
                )}
              />
            )}
          />
          <Box>
            <Button
              primary
              type="submit"
              data-testid={`submitAddInvitation${kind}Button`}
            >
              Submit
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

const UserInvitations = () => {
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const { data: streams } = useGetStreamsQuery();
  const allGroups = useGetGroupsQuery().data?.all;
  // Invite links must name a backend; offer the first configured one.
  const authBackends = (useGetConfigQuery().data as any)?.authBackends ?? [];
  const [rowsPerPage, setRowsPerPage] = useState(DEFAULT_NUM_PER_PAGE);
  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: DEFAULT_NUM_PER_PAGE,
  });
  const { data: invitationsData } = useGetInvitationsQuery(fetchParams);
  const [inviteUser] = useInviteUserMutation();
  const [updateInvitation] = useUpdateInvitationMutation();
  const [deleteInvitation] = useDeleteInvitationMutation();
  const [csvData, setCsvData] = useState("");
  const [tableFilterList, setTableFilterList] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const [openDialog, setOpenDialog] = useState<string | null>(null);
  const [clickedInvitation, setClickedInvitation] = useState<any>(null);

  const {
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm();

  if (!allGroups?.length || !streams) return null;

  if (
    !currentUser?.permissions?.includes("System admin") &&
    !currentUser?.permissions?.includes("Manage users")
  )
    return <div>Access denied: Insufficient permissions.</div>;

  const groups = allGroups.filter((group) => !group["single_user_group"]);

  const updateAndNotify = async (
    invitationID: any,
    payload: any,
    message = "Invitation successfully updated.",
    resetValues?: any,
  ) => {
    try {
      await updateInvitation({ invitationID, payload }).unwrap();
      dispatch(showNotification(message));
      if (resetValues) {
        reset(resetValues);
        setOpenDialog(null);
        setClickedInvitation(null);
      }
    } catch {
      // error notification handled by the base query
    }
  };

  const handleDeleteEntity = (invitation: any, kind: EntityKind, id: any) => {
    const { field, payloadKey } = ENTITIES[kind];
    return updateAndNotify(invitation.id, {
      [payloadKey]: invitation[field]
        ?.filter((entity: any) => entity.id !== id)
        ?.map((entity: any) => entity.id),
    });
  };

  const handleAddEntities = (kind: EntityKind) => (formData: any) => {
    const { field, payloadKey } = ENTITIES[kind];
    const ids = new Set([
      ...(clickedInvitation[field] ?? []).map((entity: any) => entity.id),
      ...formData[`invitation${kind}`].map((entity: any) => entity.id),
    ]);
    return updateAndNotify(
      clickedInvitation.id,
      { [payloadKey]: [...ids] },
      undefined,
      { [`invitation${kind}`]: [] },
    );
  };

  const handleUpdateInvitationRole = (formData: any) =>
    updateAndNotify(
      clickedInvitation.id,
      { role: formData.invitationRole },
      undefined,
      { invitationRole: "" },
    );

  const handleEditUserExpirationDate = (formData: any) => {
    if (!dayjs.utc(formData.date).isValid()) {
      dispatch(
        showNotification(
          "Invalid date. Please use MM/DD/YYYY format.",
          "error",
        ),
      );
      return undefined;
    }
    return updateAndNotify(
      clickedInvitation.id,
      { userExpirationDate: dayjs.utc(formData.date).toISOString() },
      "User expiration date successfully updated.",
      { date: null },
    );
  };

  const handleDeleteInvitation = async () => {
    setOpenDialog(null);
    try {
      await deleteInvitation(clickedInvitation.id).unwrap();
      dispatch(showNotification("Invitation successfully deleted."));
    } catch {
      // error notification handled by the base query
    }
  };

  const handleClickAddUsers = async () => {
    const parseList = (value: string, options?: any) =>
      PapaParse.parse(value.trim(), { delimiter: " ", ...options }).data[0];
    const rows = PapaParse.parse(csvData.trim(), {
      delimiter: ",",
      skipEmptyLines: "greedy",
    }).data as any[];
    try {
      await Promise.all(
        rows.map((row: any) =>
          inviteUser({
            userEmail: row[0].trim(),
            streamIDs: parseList(row[1]),
            groupIDs: parseList(row[2]),
            groupAdmin: parseList(row[3], {
              dynamicTyping: true,
              quotes: false,
            }),
            userExpirationDate: row[4]?.trim(),
          }).unwrap(),
        ),
      );
      dispatch(showNotification("User(s) invitation(s) successfully created."));
      setCsvData("");
    } catch {
      // error notification handled by the base query
    }
  };

  const handleFilterSubmit = (formData: any) => {
    Object.keys(formData).forEach(
      (key) => !formData[key] && delete formData[key],
    );
    setTableFilterList(
      Object.entries(formData).map(([key, value]) => `${key}: ${value}`),
    );
    setFetchParams({
      pageNumber: 1,
      numPerPage: fetchParams.numPerPage,
      ...formData,
    });
    setFilterOpen(false);
  };

  const handleFilterChipDelete = (chip: string) => {
    const data: any = {};
    tableFilterList
      .filter((c) => c !== chip)
      .forEach((filterChip) => {
        const [key, value] = filterChip.split(": ");
        if (key) {
          data[key] = value;
        }
      });
    handleFilterSubmit(data);
  };

  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    setFetchParams({
      ...fetchParams,
      numPerPage: model.pageSize,
      pageNumber: model.page + 1,
    });
  };

  const openInvitationDialog = (invitation: any, dialog: string) => {
    setClickedInvitation(invitation);
    setOpenDialog(dialog);
  };

  const handleCopyInvitationLink = (invitation: any) => {
    const appBaseUrl = `${window.location.protocol}//${window.location.host}`;
    navigator.clipboard.writeText(
      `${appBaseUrl}/login/${authBackends[0]?.name}/?invite_token=${invitation.token}`,
    );
    dispatch(
      showNotification(
        `Invitation link for ${invitation.user_email} copied to clipboard.`,
        "info",
      ),
    );
  };

  const renderActions = ({ row: invitation }: any) => (
    <Box sx={cellSx}>
      <Tooltip title="Copy invitation link to clipboard">
        <IconButton
          aria-label="copy-invitation-link"
          onClick={() => handleCopyInvitationLink(invitation)}
          size="small"
        >
          <ContentCopyIcon />
        </IconButton>
      </Tooltip>
      <IconButton
        aria-label="delete-invitation"
        data-testid={`deleteInvitation_${invitation.user_email}`}
        onClick={() => openInvitationDialog(invitation, "delete")}
        size="small"
      >
        <DeleteIcon />
      </IconButton>
    </Box>
  );

  const renderRole = ({ row: invitation }: any) => (
    <Box sx={cellSx}>
      {invitation.role_id}
      <IconButton
        aria-label="edit-invitation-role"
        data-testid={`editInvitationRoleButton${invitation.user_email}`}
        onClick={() => openInvitationDialog(invitation, "role")}
        size="small"
      >
        <EditIcon color="disabled" />
      </IconButton>
    </Box>
  );

  const renderEntities = (kind: EntityKind, invitation: any) => {
    const { field, singular } = ENTITIES[kind];
    return (
      <Box sx={chipCellSx}>
        <IconButton
          aria-label={`add-invitation-${field}`}
          data-testid={`addInvitation${kind}Button${invitation.user_email}`}
          onClick={() => openInvitationDialog(invitation, field)}
          size="small"
          sx={{ p: 0.375 }}
        >
          <AddCircleIcon color="disabled" sx={{ fontSize: "1.125rem" }} />
        </IconButton>
        {invitation[field]?.map((entity: any) => (
          <Chip
            label={entity.name}
            onDelete={() => handleDeleteEntity(invitation, kind, entity.id)}
            key={entity.id}
            id={`invitation${singular}Chip_${invitation.id}_${entity.id}`}
          />
        ))}
      </Box>
    );
  };

  const renderExpirationDate = ({ row: invitation }: any) => (
    <Box
      sx={{
        ...cellSx,
        color: dayjs.utc().isAfter(invitation.user_expiration_date)
          ? "red"
          : undefined,
      }}
    >
      {invitation.user_expiration_date
        ? dayjs.utc(invitation.user_expiration_date).format("YYYY/MM/DD")
        : ""}
      <IconButton
        aria-label="edit-expiration"
        onClick={() => openInvitationDialog(invitation, "date")}
        size="small"
      >
        <EditIcon color="disabled" />
      </IconButton>
    </Box>
  );

  const columns: any[] = [
    { field: "user_email", headerName: "Invitee Email", minWidth: 180 },
    {
      field: "role",
      headerName: "Role",
      minWidth: 120,
      renderCell: renderRole,
    },
    {
      field: "groups",
      headerName: "Groups",
      minWidth: 220,
      renderCell: ({ row }: any) => renderEntities("Groups", row),
    },
    {
      field: "streams",
      headerName: "Streams",
      minWidth: 220,
      renderCell: ({ row }: any) => renderEntities("Streams", row),
    },
    {
      field: "invited_by",
      headerName: "Invited By",
      minWidth: 120,
      valueGetter: (_value: any, row: any) => row.invited_by?.username,
    },
    {
      field: "user_expiration_date",
      headerName: "User Expiration Date",
      minWidth: 180,
      renderHeader: renderExpirationDateHeader,
      renderCell: renderExpirationDate,
    },
    {
      field: "actions",
      headerName: "Actions",
      minWidth: 120,
      renderCell: renderActions,
    },
  ].map((column: any) => ({
    flex: 1,
    sortable: false,
    filterable: false,
    ...column,
  }));

  const filterFormSchema = {
    type: "object",
    properties: {
      email: { type: "string", title: "Email" },
      group: {
        title: "Group",
        type: "string",
        enum: groups.map((group) => group.name),
      },
      stream: {
        title: "Stream",
        type: "string",
        enum: streams.map((stream: any) => stream.name),
      },
      invitedBy: { type: "string", title: "Invited by" },
    },
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box data-testid="pendingInvitations">
        <StyledDataGrid
          autoHeight
          columns={columns}
          rows={invitationsData?.invitations || []}
          getRowId={(row: any) => row.id}
          getRowHeight={() => "auto"}
          paginationMode="server"
          sortingMode="server"
          rowCount={invitationsData?.totalMatches ?? 0}
          paginationModel={{
            page: fetchParams.pageNumber - 1,
            pageSize: rowsPerPage,
          }}
          onPaginationModelChange={handlePaginationModelChange}
          pageSizeOptions={PAGE_SIZE_OPTIONS}
          disableColumnFilter
          slots={{ toolbar: InvitationsToolbar }}
          slotProps={{
            toolbar: {
              filters: tableFilterList,
              onOpenFilters: () => setFilterOpen(true),
              onDeleteFilter: handleFilterChipDelete,
            },
          }}
          showToolbar
        />
      </Box>
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: 2,
        }}
      >
        <Typography variant="h6">Bulk Invite New Users</Typography>
        <Box>
          <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
            email,streamIDs,groupIDs,groupAdmin,expirationDate
          </Typography>
          <Typography variant="caption" color="text.secondary">
            One invitation per line, no space after the commas. Stream IDs,
            group IDs and the true/false admin flags are space-separated lists;
            the expiration date is optional.
          </Typography>
        </Box>
        <TextareaAutosize
          placeholder={SAMPLE_CSV_TEXT}
          name="bulkInviteCSVInput"
          style={{ height: "15rem", width: "50rem" }}
          onChange={(e) => setCsvData(e.target.value)}
          value={csvData}
        />
        <Button
          secondary
          data-testid="bulkAddUsersButton"
          onClick={handleClickAddUsers}
        >
          Add Users
        </Button>
      </Paper>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>
          <Form
            schema={filterFormSchema as any}
            validator={validator}
            onSubmit={
              (({ formData }: { formData: any }) => {
                handleFilterSubmit(formData);
              }) as any
            }
          />
        </DialogContent>
      </Dialog>
      <AddEntitiesDialog
        kind="Groups"
        open={openDialog === "groups"}
        onClose={() => setOpenDialog(null)}
        email={clickedInvitation?.user_email}
        options={groups.filter(
          (group) =>
            !clickedInvitation?.groups?.some((g: any) => g.id === group.id),
        )}
        control={control}
        error={!!errors["invitationGroups"]}
        onSubmit={handleSubmit(handleAddEntities("Groups"))}
      />
      <AddEntitiesDialog
        kind="Streams"
        open={openDialog === "streams"}
        onClose={() => setOpenDialog(null)}
        email={clickedInvitation?.user_email}
        options={streams.filter(
          (stream: any) =>
            !clickedInvitation?.streams?.some((s: any) => s.id === stream.id),
        )}
        control={control}
        error={!!errors["invitationStreams"]}
        onSubmit={handleSubmit(handleAddEntities("Streams"))}
      />
      <Dialog open={openDialog === "role"} onClose={() => setOpenDialog(null)}>
        <DialogTitle>
          {`Edit user role for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <Box
            component="form"
            onSubmit={handleSubmit(handleUpdateInvitationRole)}
            sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
          >
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
            <Box>
              <Button
                primary
                type="submit"
                name="submitEditRoleButton"
                data-testid="submitEditRoleButton"
              >
                Submit
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
      <Dialog open={openDialog === "date"} onClose={() => setOpenDialog(null)}>
        <DialogTitle>Edit user expiration date:</DialogTitle>
        <DialogContent>
          <Box
            component="form"
            onSubmit={handleSubmit(handleEditUserExpirationDate)}
            sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
          >
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
            <Box>
              <Button primary type="submit" name="submitExpirationDateButton">
                Submit
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        dialogOpen={openDialog === "delete"}
        closeDialog={() => setOpenDialog(null)}
        deleteFunction={handleDeleteInvitation}
        resourceName={`invitation for ${clickedInvitation?.user_email}`}
      />
    </Box>
  );
};

export default UserInvitations;

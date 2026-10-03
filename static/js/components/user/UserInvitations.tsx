import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import SearchableSelect from "../SearchableSelect";
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
import ExpandableCell from "../ExpandableCell";
import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT_WITH_TABS,
} from "../StyledDataGrid";
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

const dialogFormSx = {
  display: "flex",
  flexDirection: "column",
  gap: 2,
  mt: 1,
} as const;

const formatDate = (date?: string) =>
  date ? dayjs.utc(date).format("YYYY/MM/DD") : "";

const parseList = (value: string, options?: any) =>
  PapaParse.parse(value.trim(), { delimiter: " ", ...options }).data[0];

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
  <DataGridToolbar
    title="Pending Invitations"
    showQuickFilter={false}
    showExpandAll
  >
    <Tooltip title="Filter Table">
      <IconButton size="small" onClick={onOpenFilters}>
        <FilterListIcon />
      </IconButton>
    </Tooltip>
    {Object.entries(filters).map(([key, value]) => (
      <Chip
        key={key}
        label={`${key}: ${value}`}
        size="small"
        onDelete={() => onDeleteFilter(key)}
      />
    ))}
  </DataGridToolbar>
);

const AddEntitiesDialog = ({
  kind,
  open,
  onClose,
  invitation,
  entities,
  control,
  error,
  onSubmit,
}: any) => {
  const { field, singular } = ENTITIES[kind as EntityKind];
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>
        {`Add selected ${singular.toLowerCase()}s to invitation for ${invitation?.user_email}:`}
      </DialogTitle>
      <DialogContent>
        <Box component="form" onSubmit={onSubmit} sx={dialogFormSx}>
          {error && (
            <FormValidationError
              message={`Please select at least one ${singular.toLowerCase()}`}
            />
          )}
          <Controller
            name={`invitation${kind}`}
            control={control}
            rules={{ validate: (value: any) => value.length >= 1 }}
            defaultValue={[]}
            render={({ field: { onChange, value } }) => (
              <SearchableSelect
                multiple
                label={`Select ${kind}`}
                value={value}
                onChange={(_e, data) => onChange(data)}
                options={entities.filter(
                  (entity: any) =>
                    !invitation?.[field]?.some((e: any) => e.id === entity.id),
                )}
                getOptionLabel={(entity: any) => entity.name}
                filterSelectedOptions
                error={error}
                data-testid={`addInvitation${kind}Select`}
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

const UserInvitations = ({
  bulkInviteOpen,
  onCloseBulkInvite,
}: {
  bulkInviteOpen: boolean;
  onCloseBulkInvite: () => void;
}) => {
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const { data: streams } = useGetStreamsQuery();
  const allGroups = useGetGroupsQuery().data?.all;
  const authBackends = (useGetConfigQuery().data as any)?.authBackends ?? [];
  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: DEFAULT_NUM_PER_PAGE,
  });
  const { data: invitationsData, isFetching: invitationsFetching } =
    useGetInvitationsQuery(fetchParams);
  const [inviteUser] = useInviteUserMutation();
  const [updateInvitation] = useUpdateInvitationMutation();
  const [deleteInvitation] = useDeleteInvitationMutation();
  const [csvData, setCsvData] = useState("");
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
  const { pageNumber, numPerPage, ...filters } = fetchParams;
  const closeDialog = () => setOpenDialog(null);

  const runAndNotify = async (
    action: () => Promise<unknown>,
    message: string,
  ) => {
    try {
      await action();
      dispatch(showNotification(message));
      return true;
    } catch {
      // error notification handled by the base query
      return false;
    }
  };

  const updateAndNotify = async (
    invitationID: any,
    payload: any,
    message = "Invitation successfully updated.",
    resetValues?: any,
  ) => {
    const updated = await runAndNotify(
      () => updateInvitation({ invitationID, payload }).unwrap(),
      message,
    );
    if (updated && resetValues) {
      reset(resetValues);
      closeDialog();
      setClickedInvitation(null);
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

  const handleDeleteInvitation = () => {
    closeDialog();
    return runAndNotify(
      () => deleteInvitation(clickedInvitation.id).unwrap(),
      "Invitation successfully deleted.",
    );
  };

  const handleBulkInvite = async () => {
    const rows = PapaParse.parse(csvData.trim(), {
      delimiter: ",",
      skipEmptyLines: "greedy",
    }).data as any[];
    const invited = await runAndNotify(
      () =>
        Promise.all(
          rows.map((row) =>
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
        ),
      "User(s) invitation(s) successfully created.",
    );
    if (invited) {
      setCsvData("");
      onCloseBulkInvite();
    }
  };

  const handleFilterSubmit = (formData: any) => {
    setFetchParams({
      pageNumber: 1,
      numPerPage,
      ...Object.fromEntries(
        Object.entries(formData).filter(([, value]) => value),
      ),
    });
    setFilterOpen(false);
  };

  const openInvitationDialog = (invitation: any, dialog: string) => {
    setClickedInvitation(invitation);
    setOpenDialog(dialog);
  };

  const handleCopyInvitationLink = (invitation: any) => {
    navigator.clipboard.writeText(
      `${window.location.origin}/login/${authBackends[0]?.name}/?invite_token=${invitation.token}`,
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
      <Chip label={invitation.role_id} />
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
        <ExpandableCell
          items={(invitation[field] ?? []).map((entity: any) => (
            <Chip
              label={entity.name}
              onDelete={() => handleDeleteEntity(invitation, kind, entity.id)}
              key={entity.id}
              id={`invitation${singular}Chip_${invitation.id}_${entity.id}`}
            />
          ))}
        />
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
      {formatDate(invitation.user_expiration_date)}
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
      minWidth: 150,
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
      field: "created_at",
      headerName: "Sent At",
      minWidth: 120,
      valueGetter: (_value: any, row: any) => formatDate(row.created_at),
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
    <>
      <Box data-testid="pendingInvitations">
        <StyledDataGrid
          height={FULL_PAGE_HEIGHT_WITH_TABS}
          columns={columns}
          rows={invitationsData?.invitations || []}
          getRowHeight={() => "auto"}
          loading={invitationsFetching}
          paginationMode="server"
          rowCount={invitationsData?.totalMatches ?? 0}
          paginationModel={{ page: pageNumber - 1, pageSize: numPerPage }}
          onPaginationModelChange={(model: any) =>
            setFetchParams({
              ...fetchParams,
              numPerPage: model.pageSize,
              pageNumber: model.page + 1,
            })
          }
          disableColumnFilter
          slots={{ toolbar: InvitationsToolbar }}
          slotProps={{
            toolbar: {
              filters,
              onOpenFilters: () => setFilterOpen(true),
              onDeleteFilter: (key: string) =>
                handleFilterSubmit({ ...filters, [key]: undefined }),
            },
          }}
          showToolbar
        />
      </Box>
      <Dialog open={bulkInviteOpen} onClose={onCloseBulkInvite} fullWidth>
        <DialogTitle>Bulk invite new users</DialogTitle>
        <DialogContent>
          <Typography
            variant="caption"
            sx={{ display: "block", color: "text.secondary" }}
          >
            One invitation per line, no space after the commas. Stream IDs,
            group IDs and the true/false admin flags are space-separated lists;
            the expiration date is optional.
          </Typography>
          <Box
            component="form"
            onSubmit={handleSubmit(handleBulkInvite)}
            sx={dialogFormSx}
          >
            <TextField
              multiline
              minRows={8}
              name="bulkInviteCSVInput"
              label="email,streamIDs,groupIDs,groupAdmin,expirationDate"
              placeholder={SAMPLE_CSV_TEXT}
              value={csvData}
              onChange={(e) => setCsvData(e.target.value)}
              slotProps={{ htmlInput: { sx: { fontFamily: "monospace" } } }}
            />
            <Box>
              <Button primary type="submit" data-testid="bulkAddUsersButton">
                Submit
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>
          <Form
            schema={filterFormSchema as any}
            validator={validator}
            onSubmit={({ formData }: any) => handleFilterSubmit(formData)}
          />
        </DialogContent>
      </Dialog>
      {(["Groups", "Streams"] as const).map((kind) => (
        <AddEntitiesDialog
          key={kind}
          kind={kind}
          open={openDialog === ENTITIES[kind].field}
          onClose={closeDialog}
          invitation={clickedInvitation}
          entities={kind === "Groups" ? groups : streams}
          control={control}
          error={!!errors[`invitation${kind}`]}
          onSubmit={handleSubmit(handleAddEntities(kind))}
        />
      ))}
      <Dialog open={openDialog === "role"} onClose={closeDialog}>
        <DialogTitle>
          {`Edit user role for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <Box
            component="form"
            onSubmit={handleSubmit(handleUpdateInvitationRole)}
            sx={dialogFormSx}
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
      <Dialog open={openDialog === "date"} onClose={closeDialog}>
        <DialogTitle>Edit user expiration date:</DialogTitle>
        <DialogContent>
          <Box
            component="form"
            onSubmit={handleSubmit(handleEditUserExpirationDate)}
            sx={dialogFormSx}
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
        closeDialog={closeDialog}
        deleteFunction={handleDeleteInvitation}
        resourceName={`invitation for ${clickedInvitation?.user_email}`}
      />
    </>
  );
};

export default UserInvitations;

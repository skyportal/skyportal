import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { alpha } from "@mui/material/styles";
import SearchableSelect from "../SearchableSelect";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import EditIcon from "@mui/icons-material/Edit";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import Tooltip from "@mui/material/Tooltip";
import HelpIcon from "@mui/icons-material/Help";
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

const expiredSx = (theme: any) => ({
  "& .expired": { bgcolor: alpha(theme.palette.error.main, 0.08) },
  "& .expired:hover": { bgcolor: alpha(theme.palette.error.main, 0.14) },
  "& .expired-date": { color: "error.main" },
});

const formatDate = (date?: string) =>
  date ? dayjs.utc(date).format("YYYY/MM/DD") : "";

const isPast = (date: any) => !!date && dayjs.utc(date).isBefore(dayjs.utc());

const parseList = (value: string, options?: any) =>
  PapaParse.parse(value.trim(), { delimiter: " ", ...options }).data[0];

const parseCsv = (csv: string) =>
  PapaParse.parse(csv.trim(), { delimiter: ",", skipEmptyLines: "greedy" })
    .data as any[];

const validateBulkInvite = (csv: string) => {
  const rows = parseCsv(csv);
  if (!rows.length) return "Please enter at least one invitation";
  const invalid = rows.find(
    (row) =>
      row.length < 4 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row[0].trim()),
  );
  return invalid ? `Invalid line: ${invalid.join(",")}` : true;
};

const renderExpirationDateHeader = () => (
  <Box sx={{ display: "flex", alignItems: "center" }}>
    Expiration Date
    <Tooltip title="This is the expiration date assigned to the new user account. On this date, the user account will be deactivated and will be unable to access the application.">
      <HelpIcon color="disabled" sx={{ height: "1rem" }} />
    </Tooltip>
  </Box>
);

const InvitationsToolbar = ({ showExpired, onToggleExpired }: any) => (
  <DataGridToolbar title="Pending Invitations" showFilter showExpandAll>
    <FormControlLabel
      control={
        <Switch
          checked={showExpired}
          onChange={onToggleExpired}
          color="primary"
          data-testid="showExpiredInvitationsToggle"
        />
      }
      label="Show Expired Invitations"
      sx={{ mr: 2 }}
    />
  </DataGridToolbar>
);

const EditableCell = ({ children, onEdit, ...buttonProps }: any) => (
  <Box sx={cellSx}>
    {children}
    <IconButton size="small" onClick={onEdit} {...buttonProps}>
      <EditIcon color="disabled" />
    </IconButton>
  </Box>
);

const EntitiesCell = ({ kind, invitation, onAdd, onDelete }: any) => {
  const { field, singular } = ENTITIES[kind as EntityKind];
  return (
    <Box sx={chipCellSx}>
      <IconButton
        aria-label={`add-invitation-${field}`}
        data-testid={`addInvitation${kind}Button${invitation.user_email}`}
        onClick={onAdd}
        size="small"
        sx={{ p: 0.375 }}
      >
        <AddCircleIcon color="disabled" sx={{ fontSize: "1.125rem" }} />
      </IconButton>
      <ExpandableCell
        items={(invitation[field] ?? []).map((entity: any) => (
          <Chip
            label={entity.name}
            onDelete={() => onDelete(entity.id)}
            key={entity.id}
            id={`invitation${singular}Chip_${invitation.id}_${entity.id}`}
          />
        ))}
      />
    </Box>
  );
};

const FormDialog = ({
  title,
  onSubmit,
  submitProps,
  children,
  ...dialogProps
}: any) => (
  <Dialog {...dialogProps}>
    <DialogTitle>{title}</DialogTitle>
    <DialogContent>
      <Box
        component="form"
        onSubmit={onSubmit}
        sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
      >
        {children}
        <Button
          primary
          type="submit"
          sx={{ alignSelf: "flex-start" }}
          {...submitProps}
        >
          Submit
        </Button>
      </Box>
    </DialogContent>
  </Dialog>
);

const AddEntitiesDialog = ({
  kind,
  invitation,
  entities,
  control,
  error,
  ...dialogProps
}: any) => {
  const { field, singular } = ENTITIES[kind as EntityKind];
  const noun = singular.toLowerCase();
  return (
    <FormDialog
      title={`Add selected ${noun}s to invitation for ${invitation?.user_email}:`}
      submitProps={{ "data-testid": `submitAddInvitation${kind}Button` }}
      {...dialogProps}
    >
      {error && (
        <FormValidationError message={`Please select at least one ${noun}`} />
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
    </FormDialog>
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
  const { data: streams } = useGetStreamsQuery();
  const allGroups = useGetGroupsQuery().data?.all;
  const config = useGetConfigQuery().data as any;
  const { data: invitationsData, isFetching: invitationsFetching } =
    useGetInvitationsQuery();
  const [inviteUser] = useInviteUserMutation();
  const [updateInvitation] = useUpdateInvitationMutation();
  const [deleteInvitation] = useDeleteInvitationMutation();
  const [showExpired, setShowExpired] = useState(false);
  const [openDialog, setOpenDialog] = useState<string | null>(null);
  const [clickedInvitation, setClickedInvitation] = useState<any>(null);

  const {
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm();

  if (!allGroups || !streams || !config) return null;

  const groups = allGroups.filter((group) => !group["single_user_group"]);
  const closeDialog = () => setOpenDialog(null);

  const isLinkExpired = (invitation: any) =>
    isPast(
      dayjs
        .utc(invitation.created_at)
        .add(config.invitationsDaysUntilExpiry, "day"),
    );
  const isAccountExpired = (invitation: any) =>
    isPast(invitation.user_expiration_date);
  const isExpired = (invitation: any) =>
    isLinkExpired(invitation) || isAccountExpired(invitation);

  const invitations = invitationsData?.invitations ?? [];

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
    resetValues?: any,
    message = "Invitation successfully updated.",
  ) => {
    const updated = await runAndNotify(
      () => updateInvitation({ invitationID, payload }).unwrap(),
      message,
    );
    if (updated && resetValues) {
      reset(resetValues);
      closeDialog();
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
      { [`invitation${kind}`]: [] },
    );
  };

  const handleUpdateInvitationRole = (formData: any) =>
    updateAndNotify(
      clickedInvitation.id,
      { role: formData.invitationRole },
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
      { date: null },
      "User expiration date successfully updated.",
    );
  };

  const handleDeleteInvitation = () => {
    closeDialog();
    return runAndNotify(
      () => deleteInvitation(clickedInvitation.id).unwrap(),
      "Invitation successfully deleted.",
    );
  };

  const handleBulkInvite = async (formData: any) => {
    const rows = parseCsv(formData.bulkInviteCSV);
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
      reset({ bulkInviteCSV: "" });
      onCloseBulkInvite();
    }
  };

  const openInvitationDialog = (invitation: any, dialog: string) => {
    setClickedInvitation(invitation);
    setOpenDialog(dialog);
  };

  const handleCopyInvitationLink = (invitation: any) => {
    navigator.clipboard.writeText(
      `${window.location.origin}/login/${config.authBackends?.[0]?.name}/?invite_token=${invitation.token}`,
    );
    dispatch(
      showNotification(
        `Invitation link for ${invitation.user_email} copied to clipboard.`,
        "info",
      ),
    );
  };

  const entitiesColumn = (kind: EntityKind) => ({
    field: ENTITIES[kind].field,
    headerName: kind,
    minWidth: 220,
    valueGetter: (value: any[]) =>
      value?.map((entity) => entity.name).join(", "),
    renderCell: ({ row }: any) => (
      <EntitiesCell
        kind={kind}
        invitation={row}
        onAdd={() => openInvitationDialog(row, ENTITIES[kind].field)}
        onDelete={(id: any) => handleDeleteEntity(row, kind, id)}
      />
    ),
  });

  const columns: any[] = [
    { field: "user_email", headerName: "Invitee Email", minWidth: 180 },
    {
      field: "role_id",
      headerName: "Role",
      minWidth: 150,
      renderCell: ({ row }: any) => (
        <EditableCell
          aria-label="edit-invitation-role"
          data-testid={`editInvitationRoleButton${row.user_email}`}
          onEdit={() => openInvitationDialog(row, "role")}
        >
          <Chip label={row.role_id} />
        </EditableCell>
      ),
    },
    entitiesColumn("Groups"),
    entitiesColumn("Streams"),
    {
      field: "invited_by",
      headerName: "Invited By",
      minWidth: 120,
      valueGetter: (value: any) => value?.username,
    },
    {
      field: "created_at",
      headerName: "Sent At",
      minWidth: 120,
      valueFormatter: formatDate,
      cellClassName: ({ row }: any) =>
        isLinkExpired(row) ? "expired-date" : "",
    },
    {
      field: "user_expiration_date",
      headerName: "User Expiration Date",
      minWidth: 180,
      renderHeader: renderExpirationDateHeader,
      cellClassName: ({ row }: any) =>
        isAccountExpired(row) ? "expired-date" : "",
      renderCell: ({ row }: any) => (
        <EditableCell
          aria-label="edit-expiration"
          onEdit={() => openInvitationDialog(row, "date")}
        >
          {formatDate(row.user_expiration_date)}
        </EditableCell>
      ),
    },
    {
      field: "actions",
      headerName: "Actions",
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) => (
        <Box sx={cellSx}>
          <Tooltip title="Copy invitation link to clipboard">
            <IconButton
              aria-label="copy-invitation-link"
              onClick={() => handleCopyInvitationLink(row)}
              size="small"
            >
              <ContentCopyIcon />
            </IconButton>
          </Tooltip>
          <IconButton
            aria-label="delete-invitation"
            data-testid={`deleteInvitation_${row.user_email}`}
            onClick={() => openInvitationDialog(row, "delete")}
            size="small"
          >
            <DeleteIcon />
          </IconButton>
        </Box>
      ),
    },
  ].map((column) => ({ flex: 1, ...column }));

  return (
    <>
      <Box data-testid="pendingInvitations">
        <StyledDataGrid
          height={FULL_PAGE_HEIGHT_WITH_TABS}
          columns={columns}
          rows={
            showExpired ? invitations : invitations.filter((i) => !isExpired(i))
          }
          getRowHeight={() => "auto"}
          getRowClassName={({ row }: any) => (isExpired(row) ? "expired" : "")}
          loading={invitationsFetching}
          initialState={{
            sorting: { sortModel: [{ field: "created_at", sort: "desc" }] },
          }}
          slots={{ toolbar: InvitationsToolbar }}
          slotProps={{
            toolbar: {
              showExpired,
              onToggleExpired: () => setShowExpired(!showExpired),
            },
          }}
          showToolbar
          sx={expiredSx}
        />
      </Box>
      <FormDialog
        open={bulkInviteOpen}
        onClose={onCloseBulkInvite}
        fullWidth
        title="Bulk invite new users"
        onSubmit={handleSubmit(handleBulkInvite)}
        submitProps={{ "data-testid": "bulkAddUsersButton" }}
      >
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          One invitation per line, no space after the commas. Stream IDs, group
          IDs and the true/false admin flags are space-separated lists; the
          expiration date is optional.
        </Typography>
        {!!errors["bulkInviteCSV"] && (
          <FormValidationError
            message={String(errors["bulkInviteCSV"].message)}
          />
        )}
        <Controller
          name="bulkInviteCSV"
          control={control}
          rules={{ validate: validateBulkInvite }}
          defaultValue=""
          render={({ field: { onChange, value } }) => (
            <TextField
              multiline
              minRows={8}
              name="bulkInviteCSVInput"
              label="email,streamIDs,groupIDs,groupAdmin,expirationDate"
              placeholder={SAMPLE_CSV_TEXT}
              value={value}
              onChange={onChange}
              error={!!errors["bulkInviteCSV"]}
              slotProps={{
                htmlInput: { sx: { fontFamily: "monospace" } },
              }}
            />
          )}
        />
      </FormDialog>
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
      <FormDialog
        open={openDialog === "role"}
        onClose={closeDialog}
        title={`Edit user role for ${clickedInvitation?.user_email}:`}
        onSubmit={handleSubmit(handleUpdateInvitationRole)}
        submitProps={{ "data-testid": "submitEditRoleButton" }}
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
      </FormDialog>
      <FormDialog
        open={openDialog === "date"}
        onClose={closeDialog}
        title="Edit user expiration date:"
        onSubmit={handleSubmit(handleEditUserExpirationDate)}
      >
        <Controller
          name="date"
          control={control}
          defaultValue={null}
          render={({ field: { onChange, value } }) => (
            <DatePicker
              value={value}
              onChange={onChange}
              label="Expiration date (UTC)"
            />
          )}
        />
      </FormDialog>
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

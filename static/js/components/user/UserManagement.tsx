import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import { createFilterOptions } from "@mui/material/Autocomplete";
import SearchableSelect from "../SearchableSelect";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import HelpIcon from "@mui/icons-material/Help";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import FormValidationError from "../FormValidationError";
import Spinner from "../Spinner";
import UserInvitations from "./UserInvitations";
import UpdateUserParameter from "./UpdateUserParameter";
import {
  useAddGroupUserMutation,
  useDeleteGroupUserMutation,
  useGetGroupsQuery,
} from "../../ducks/groups";
import { usePatchUserMutation } from "../../ducks/users";
import { useGetUsersManagementQuery } from "../../ducks/users_management";
import { useGetConfigQuery } from "../../ducks/config";
import {
  useGetStreamsQuery,
  useAddStreamUserMutation,
  useDeleteStreamUserMutation,
} from "../../ducks/streams";
import {
  useGetAclsQuery,
  useAddUserAclsMutation,
  useDeleteUserAclMutation,
} from "../../ducks/acls";
import {
  useGetRolesQuery,
  useAddUserRolesMutation,
  useDeleteUserRoleMutation,
} from "../../ducks/roles";
import {
  useGetProfileQuery,
  useUpdateBasicUserInfoMutation,
} from "../../ducks/profile";
import { useAppDispatch } from "../../types/hooks";

dayjs.extend(utc);

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200];
const DEFAULT_NUM_PER_PAGE = 25;

const cellSx = {
  display: "flex",
  alignItems: "center",
  gap: 0.5,
  flexWrap: "wrap",
  "& .MuiChip-deleteIcon": { display: "none" },
  "& .MuiChip-root:hover .MuiChip-deleteIcon": { display: "inline-block" },
} as const;

const revealOnHoverSx = {
  ...cellSx,
  "& > .MuiIconButton-root, & > .MuiSvgIcon-root": { display: "none" },
  ".MuiDataGrid-cell:hover & > .MuiIconButton-root": { display: "inline-flex" },
  ".MuiDataGrid-cell:hover & > .MuiSvgIcon-root": { display: "inline-block" },
} as const;

const dialogFormSx = {
  display: "flex",
  flexDirection: "column",
  gap: 2,
  mt: 1,
} as const;

const filterOptions = createFilterOptions();

const itemKey = (item: any) => item?.id ?? item;
const itemLabel = (item: any) => item?.name ?? item;

const headerWithHelp = (label: string, help: any) => (
  <Box sx={{ display: "flex", alignItems: "center" }}>
    {label}
    <Tooltip title={help}>
      <HelpIcon color="disabled" sx={{ height: "1rem" }} />
    </Tooltip>
  </Box>
);

const editableCell = (user: any, parameter: string | string[]) => (
  <Box sx={revealOnHoverSx}>
    {(Array.isArray(parameter) ? parameter : [parameter])
      .map((name) => user[name])
      .filter(Boolean)
      .join(" ")}
    <UpdateUserParameter user={user} parameter={parameter} />
  </Box>
);

const UsersToolbar = ({ includeExpired, onToggleExpired }: any) => (
  <DataGridToolbar
    title="Manage Users"
    showFilter
    quickFilterTestId="users-quick-filter"
  >
    <FormControlLabel
      control={
        <Switch
          checked={includeExpired}
          onChange={onToggleExpired}
          color="primary"
          data-testid="showExpiredUsersToggle"
        />
      }
      label="Show Expired Users"
      sx={{ mr: 2 }}
    />
  </DataGridToolbar>
);

const AddEntitiesDialog = ({
  open,
  onClose,
  title,
  name,
  label,
  errorMessage,
  options,
  getOptionLabel,
  selectTestId,
  submitId,
  control,
  invalid,
  onSubmit,
}: any) => (
  <Dialog open={open} onClose={onClose}>
    <DialogTitle>{title}</DialogTitle>
    <DialogContent>
      <Box component="form" onSubmit={onSubmit} sx={dialogFormSx}>
        {invalid && <FormValidationError message={errorMessage} />}
        <Controller
          name={name}
          control={control}
          rules={{ validate: (value: any) => value.length >= 1 }}
          defaultValue={[]}
          render={({ field: { onChange, value } }) => (
            <SearchableSelect
              multiple
              label={label}
              value={value}
              onChange={(_e, data) => onChange(data)}
              options={options}
              getOptionLabel={getOptionLabel}
              filterSelectedOptions
              error={invalid}
              data-testid={selectTestId}
            />
          )}
        />
        <Box>
          <Button primary type="submit" data-testid={submitId}>
            Submit
          </Button>
        </Box>
      </Box>
    </DialogContent>
  </Dialog>
);

const UserManagement = () => {
  const dispatch = useAppDispatch();
  const { data: currentUser } = useGetProfileQuery();
  const { invitationsEnabled } = (useGetConfigQuery().data as any) ?? {};
  const { data: acls } = useGetAclsQuery();
  const { data: roles } = useGetRolesQuery();
  const { data: streams } = useGetStreamsQuery();
  const allGroups = useGetGroupsQuery().data?.all;
  const [patchUser] = usePatchUserMutation();
  const [updateBasicUserInfo] = useUpdateBasicUserInfoMutation();
  const [addGroupUser] = useAddGroupUserMutation();
  const [deleteGroupUser] = useDeleteGroupUserMutation();
  const [addStreamUser] = useAddStreamUserMutation();
  const [deleteStreamUser] = useDeleteStreamUserMutation();
  const [addUserAcls] = useAddUserAclsMutation();
  const [deleteUserAcl] = useDeleteUserAclMutation();
  const [addUserRoles] = useAddUserRolesMutation();
  const [deleteUserRole] = useDeleteUserRoleMutation();
  const [includeExpired, setIncludeExpired] = useState(false);
  const [openDialog, setOpenDialog] = useState<string | null>(null);
  const [removeExpirationOpen, setRemoveExpirationOpen] = useState(false);
  const [clickedUser, setClickedUser] = useState<any>(null);
  const {
    data: usersManagementData,
    refetch: refetchUsersManagement,
    isFetching: usersManagementFetching,
  } = useGetUsersManagementQuery({ includeExpired });

  const {
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm();

  if (
    !currentUser?.username?.length ||
    !allGroups?.length ||
    !streams ||
    !acls?.length ||
    !roles?.length
  )
    return <Spinner />;

  if (
    !currentUser.permissions?.includes("System admin") &&
    !currentUser.permissions?.includes("Manage users")
  )
    return <div>Access denied: Insufficient permissions.</div>;

  const groups = allGroups.filter((group) => !group["single_user_group"]);

  const runAndNotify = async (
    action: () => Promise<any>,
    message: string,
    closeDialog = true,
  ) => {
    try {
      await action();
      dispatch(showNotification(message));
      if (closeDialog) {
        reset();
        setOpenDialog(null);
      }
      await refetchUsersManagement();
      if (closeDialog) setClickedUser(null);
    } catch {
      // error notification handled by the base query
    }
  };

  const CHIP_CELLS: Record<string, any> = {
    roles: {
      aria: "add-role",
      addTestId: "addUserRolesButton",
      deleteTestId: "deleteUserRoleButton",
      items: (user: any) => user.roles,
      onDelete: (user: any, role: any) =>
        runAndNotify(
          () => deleteUserRole({ userID: user.id, role }).unwrap(),
          "User role successfully removed.",
          false,
        ),
    },
    acls: {
      aria: "add-acl",
      addTestId: "addUserACLsButton",
      deleteTestId: "deleteUserACLButton",
      items: (user: any) => user.acls,
      onDelete: (user: any, acl: any) =>
        runAndNotify(
          () => deleteUserAcl({ userID: user.id, acl }).unwrap(),
          "User ACL successfully removed.",
          false,
        ),
    },
    affiliations: {
      aria: "add-affiliation",
      addTestId: "addUserAffiliationsButton",
      deleteTestId: "deleteUserAffiliationsButton",
      items: (user: any) => user.affiliations,
      onDelete: (user: any, affiliation: any) =>
        runAndNotify(
          () =>
            updateBasicUserInfo({
              formData: {
                affiliations: user.affiliations.filter(
                  (value: any) => value !== affiliation,
                ),
              },
              user_id: user.id,
            }).unwrap(),
          "Successfully deleted user's affiliation.",
          false,
        ),
    },
    groups: {
      aria: "add-group",
      addTestId: "addUserGroupsButton",
      deleteTestId: "deleteGroupUserButton",
      items: (user: any) =>
        user.groups?.filter((group: any) => !group.single_user_group),
      onDelete: (user: any, group: any) =>
        runAndNotify(
          () =>
            deleteGroupUser({ userID: user.id, group_id: group.id }).unwrap(),
          "User successfully removed from specified group.",
          false,
        ),
    },
    streams: {
      aria: "add-stream",
      addTestId: "addUserStreamsButton",
      deleteTestId: "deleteStreamUserButton",
      items: (user: any) => user.streams,
      onDelete: (user: any, stream: any) =>
        runAndNotify(
          () =>
            deleteStreamUser({
              user_id: user.id,
              stream_id: stream.id,
            }).unwrap(),
          "Stream access successfully revoked.",
          false,
        ),
    },
  };

  const openUserDialog = (user: any, dialog: string) => {
    reset({ affiliations: user.affiliations });
    setClickedUser(user);
    setOpenDialog(dialog);
  };

  const chipCell = (user: any, kind: string) => {
    const { aria, addTestId, deleteTestId, items, onDelete } = CHIP_CELLS[kind];
    return (
      <Box sx={revealOnHoverSx}>
        <IconButton
          aria-label={aria}
          data-testid={`${addTestId}${user.id}`}
          onClick={() => openUserDialog(user, kind)}
          size="small"
          sx={{ p: 0.375 }}
        >
          <AddCircleIcon color="disabled" sx={{ fontSize: "1.125rem" }} />
        </IconButton>
        {items(user)?.map((item: any) => (
          <Chip
            key={itemKey(item)}
            label={itemLabel(item)}
            onDelete={() => onDelete(user, item)}
            data-testid={`${deleteTestId}_${user.id}_${itemKey(item)}`}
          />
        ))}
      </Box>
    );
  };

  const handleAddUserToGroups = (formData: any) =>
    runAndNotify(
      () =>
        Promise.all(
          formData.groups.map((group: any) =>
            addGroupUser({
              userID: clickedUser.id,
              admin: false,
              group_id: group.id,
            } as any).unwrap(),
          ),
        ),
      "User successfully added to specified group(s).",
    );

  const handleAddUserToStreams = (formData: any) =>
    runAndNotify(
      () =>
        Promise.all(
          formData.streams.map((stream: any) =>
            addStreamUser({
              user_id: clickedUser.id,
              stream_id: stream.id,
            }).unwrap(),
          ),
        ),
      "User successfully added to specified stream(s).",
    );

  const handleAddUserACLs = (formData: any) =>
    runAndNotify(
      () =>
        addUserAcls({ userID: clickedUser.id, aclIds: formData.acls }).unwrap(),
      "User successfully granted specified ACL(s).",
    );

  const handleAddUserRoles = (formData: any) =>
    runAndNotify(
      () =>
        addUserRoles({
          userID: clickedUser.id,
          roleIds: formData.roles.map((role: any) => role.id),
        }).unwrap(),
      "User successfully granted specified role(s).",
    );

  const handleAddUserAffiliations = (formData: any) =>
    runAndNotify(
      () =>
        updateBasicUserInfo({
          formData: { affiliations: formData.affiliations },
          user_id: clickedUser.id,
        }).unwrap(),
      "Successfully updated user's affiliations.",
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
    return runAndNotify(
      () =>
        patchUser({
          id: clickedUser.id,
          data: { expirationDate: dayjs.utc(formData.date).toISOString() },
        }).unwrap(),
      "User expiration date successfully updated.",
    );
  };

  const handleRemoveUserExpirationDate = () =>
    runAndNotify(
      () =>
        patchUser({
          id: clickedUser.id,
          data: { expirationDate: null },
        }).unwrap(),
      "User expiration date successfully removed.",
    );

  const columns: any[] = [
    {
      field: "name",
      headerName: "Name",
      minWidth: 150,
      valueGetter: (_value: any, row: any) =>
        [row.first_name, row.last_name].filter(Boolean).join(" "),
      renderCell: ({ row }: any) =>
        editableCell(row, ["first_name", "last_name"]),
    },
    {
      field: "username",
      headerName: "Username",
      minWidth: 130,
      renderCell: ({ row }: any) => editableCell(row, "username"),
    },
    {
      field: "created_at",
      headerName: "Created At",
      minWidth: 120,
      renderCell: ({ row }: any) =>
        row.created_at ? dayjs.utc(row.created_at).format("YYYY/MM/DD") : "",
    },
    {
      field: "affiliations",
      headerName: "Affiliations",
      minWidth: 200,
      valueGetter: (_value: any, row: any) => row.affiliations?.join(", "),
      renderHeader: () =>
        headerWithHelp(
          "Affiliations",
          <p>
            These are affiliations. They can be used when writing papers or
            circulars
          </p>,
        ),
      renderCell: ({ row }: any) => chipCell(row, "affiliations"),
    },
    {
      field: "contact_email",
      headerName: "Email",
      minWidth: 180,
      renderCell: ({ row }: any) => editableCell(row, "contact_email"),
    },
    {
      field: "roles",
      headerName: "Roles",
      minWidth: 200,
      valueGetter: (_value: any, row: any) => row.roles?.join(", "),
      renderHeader: () =>
        headerWithHelp(
          "Roles",
          <>
            <b>Each role is associated with the following ACLs:</b>
            <ul>
              {roles.map((role: any) => (
                <li key={role.id}>
                  {role.id}: {role.acls.join(", ")}
                </li>
              ))}
            </ul>
          </>,
        ),
      renderCell: ({ row }: any) => chipCell(row, "roles"),
    },
    {
      field: "addition",
      headerName: "Additional ACLS",
      minWidth: 200,
      valueGetter: (_value: any, row: any) => row.acls?.join(", "),
      renderHeader: () =>
        headerWithHelp(
          "ACLs",
          <p>
            These are in addition to those ACLs associated with user role(s).
            See help icon tooltip in roles column header for those ACLs.
          </p>,
        ),
      renderCell: ({ row }: any) => chipCell(row, "acls"),
    },
    {
      field: "groups",
      headerName: "Groups",
      minWidth: 200,
      valueGetter: (_value: any, row: any) =>
        row.groups
          ?.filter((group: any) => !group.single_user_group)
          .map((group: any) => group.name)
          .join(", "),
      renderCell: ({ row }: any) => chipCell(row, "groups"),
    },
    {
      field: "streams",
      headerName: "Streams",
      minWidth: 200,
      valueGetter: (_value: any, row: any) =>
        row.streams?.map((stream: any) => stream.name).join(", "),
      renderCell: ({ row }: any) => chipCell(row, "streams"),
    },
    {
      field: "expiration_date",
      headerName: "Expiration Date",
      minWidth: 150,
      renderHeader: () =>
        headerWithHelp(
          "Expiration Date",
          "This is the expiration date assigned to the new user account. On this date, the user account will be deactivated and will be unable to access the application.",
        ),
      renderCell: ({ row }: any) => (
        <Box
          sx={{
            ...cellSx,
            color: dayjs.utc().isAfter(row.expiration_date) ? "red" : undefined,
          }}
        >
          {row.expiration_date
            ? dayjs.utc(row.expiration_date).format("YYYY/MM/DD")
            : ""}
          <IconButton
            aria-label="edit-expiration"
            data-testid={`editUserExpirationDate${row.id}`}
            onClick={() => openUserDialog(row, "date")}
            size="small"
          >
            <EditIcon color="disabled" />
          </IconButton>
        </Box>
      ),
    },
  ].map((column: any) => ({ flex: 1, ...column }));

  const addDialogs = [
    {
      name: "groups",
      title: `Add user ${clickedUser?.username} to selected groups:`,
      label: "Select Groups",
      errorMessage: "Please select at least one group",
      options: groups.filter(
        (group) => !clickedUser?.groups?.some((g: any) => g.id === group.id),
      ),
      getOptionLabel: (group: any) => group.name,
      selectTestId: "addUserToGroupsSelect",
      submitId: "submitAddFromGroupsButton",
      onSubmit: handleSubmit(handleAddUserToGroups),
    },
    {
      name: "streams",
      title: `Grant user ${clickedUser?.username} access to selected streams:`,
      label: "Select Streams",
      errorMessage: "Please select at least one stream",
      options: streams.filter(
        (stream: any) =>
          !clickedUser?.streams?.some((s: any) => s.id === stream.id),
      ),
      getOptionLabel: (stream: any) => stream.name,
      selectTestId: "addUserToStreamsSelect",
      onSubmit: handleSubmit(handleAddUserToStreams),
    },
    {
      name: "acls",
      title: `Grant user ${clickedUser?.username} selected ACLs:`,
      label: "Select ACLs",
      errorMessage: "Please select at least one ACL",
      options: acls.filter(
        (acl: any) => !clickedUser?.permissions?.includes(acl),
      ),
      getOptionLabel: (acl: any) => acl,
      selectTestId: "addUserACLsSelect",
      onSubmit: handleSubmit(handleAddUserACLs),
    },
    {
      name: "roles",
      title: `Grant user ${clickedUser?.username} selected roles:`,
      label: "Select Roles",
      errorMessage: "Please select at least one role",
      options: roles.filter(
        (role: any) => !clickedUser?.roles?.includes(role.id),
      ),
      getOptionLabel: (role: any) => role.id,
      selectTestId: "addUserRolesSelect",
      onSubmit: handleSubmit(handleAddUserRoles),
    },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ height: "calc(100vh - 161px)", width: "100%" }}>
        <StyledDataGrid
          columns={columns}
          rows={usersManagementData?.users || []}
          getRowId={(row: any) => row.id}
          getRowHeight={() => "auto"}
          loading={usersManagementFetching}
          initialState={{
            pagination: { paginationModel: { pageSize: DEFAULT_NUM_PER_PAGE } },
          }}
          pageSizeOptions={PAGE_SIZE_OPTIONS}
          columnBufferPx={3000}
          slots={{ toolbar: UsersToolbar }}
          slotProps={{
            toolbar: {
              includeExpired,
              onToggleExpired: (event: any) =>
                setIncludeExpired(event.target.checked),
            },
          }}
          showToolbar
        />
      </Box>
      {invitationsEnabled && <UserInvitations />}
      {addDialogs.map((dialog) => (
        <AddEntitiesDialog
          key={dialog.name}
          open={openDialog === dialog.name}
          onClose={() => setOpenDialog(null)}
          control={control}
          invalid={!!errors[dialog.name]}
          {...dialog}
        />
      ))}
      <Dialog
        open={openDialog === "affiliations"}
        onClose={() => setOpenDialog(null)}
      >
        <DialogTitle>{`${clickedUser?.username} affiliations:`}</DialogTitle>
        <DialogContent>
          <Box
            component="form"
            onSubmit={handleSubmit(handleAddUserAffiliations)}
            sx={dialogFormSx}
          >
            <Controller
              name="affiliations"
              control={control}
              defaultValue={clickedUser?.affiliations}
              render={({ field: { onChange, value } }) => (
                <SearchableSelect
                  multiple
                  freeSolo
                  label="Select Affiliations"
                  value={value}
                  onChange={(_e, data) => onChange(data)}
                  options={clickedUser?.affiliations ?? []}
                  filterOptions={(options, params) => {
                    const filtered = filterOptions(options, params);
                    const { inputValue } = params;
                    if (inputValue !== "" && !options.includes(inputValue)) {
                      filtered.push(inputValue);
                    }
                    return filtered;
                  }}
                  getOptionLabel={(affiliation: any) => affiliation}
                  data-testid="addUserAffiliationsSelect"
                  textFieldProps={{
                    "data-testid": "addUserAffiliationsTextField",
                  }}
                />
              )}
            />
            <Box>
              <Button primary type="submit" name="submitAddAffiliationsButton">
                Submit
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
      <Dialog open={openDialog === "date"} onClose={() => setOpenDialog(null)}>
        <DialogTitle>
          {`Edit user ${clickedUser?.username} expiration date:`}
        </DialogTitle>
        <DialogContent>
          <Box
            component="form"
            onSubmit={handleSubmit(handleEditUserExpirationDate)}
            sx={dialogFormSx}
          >
            <Controller
              name="date"
              control={control}
              defaultValue={null}
              render={({ field: { onChange, value } }) => (
                <DatePicker
                  value={value}
                  onChange={(newValue) => onChange(newValue)}
                  slotProps={{
                    textField: { variant: "outlined" },
                    field: { clearable: true } as any,
                  }}
                  label="Expiration date (UTC)"
                  {...({ showTodayButton: false } as any)}
                />
              )}
            />
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button
                primary
                type="submit"
                name="submitExpirationDateButton"
                data-testid="submitExpirationDateButton"
              >
                Submit
              </Button>
              <Button
                secondary
                onClick={(e: any) => {
                  e.preventDefault();
                  setRemoveExpirationOpen(true);
                }}
                name="removeExpirationDateButton"
              >
                Remove Expiration Date
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
      <Dialog
        open={removeExpirationOpen}
        onClose={() => setRemoveExpirationOpen(false)}
      >
        <DialogTitle>Confirm Removal</DialogTitle>
        <DialogContent>
          <p>
            Are you sure you want to remove the expiration date for user{" "}
            <strong>{clickedUser?.username}</strong>? This will reactivate their
            account.
          </p>
          <Box sx={{ display: "flex", gap: 1, mt: 2 }}>
            <Button
              primary
              onClick={() => {
                handleRemoveUserExpirationDate();
                setRemoveExpirationOpen(false);
                setOpenDialog(null);
              }}
              name="confirmRemoveExpirationButton"
            >
              Yes, Remove Expiration Date
            </Button>
            <Button
              secondary
              onClick={() => setRemoveExpirationOpen(false)}
              name="cancelRemoveExpirationButton"
            >
              Cancel
            </Button>
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default UserManagement;

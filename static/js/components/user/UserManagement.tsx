import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";

import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import HelpIcon from "@mui/icons-material/Help";
import EditIcon from "@mui/icons-material/Edit";
import FilterListIcon from "@mui/icons-material/FilterList";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { makeStyles } from "tss-react/mui";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import FormValidationError from "../FormValidationError";
import UserInvitations from "./UserInvitations";
import UpdateUserParameter from "./UpdateUserParameter";
import * as groupsActions from "../../ducks/groups";
import { patchUser } from "../../ducks/users";
import {
  fetchUsersManagement,
  setUsersManagementFetchParams,
} from "../../ducks/users_management";
import * as streamsActions from "../../ducks/streams";
import * as invitationsActions from "../../ducks/invitations";
import {
  useGetAclsQuery,
  useAddUserAclsMutation,
  useDeleteUserAclMutation,
} from "../../ducks/acls";
import * as rolesActions from "../../ducks/roles";
import Spinner from "../Spinner";

import * as ProfileActions from "../../ducks/profile";
import { useAppDispatch, useAppSelector } from "../../types/hooks";

dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  icon: {
    height: "1rem",
  },
  submitButton: {
    marginTop: "1rem",
  },
  expired: {
    color: "red",
  },
}));

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200];

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map are not server-sortable.
const SERVER_SORT_FIELD: Record<string, string> = {
  username: "username",
  created_at: "created_at",
};

const defaultNumPerPage = 25;

const UserManagement = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [rowsPerPage, setRowsPerPage] = useState(defaultNumPerPage);
  const [queryInProgress, setQueryInProgress] = useState(false);
  const [sortModel, setSortModel] = useState<any[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);
  const { invitationsEnabled } = useAppSelector((state) => state["config"]);
  const currentUser = useAppSelector((state) => state.profile);
  const { users, totalMatches } = useAppSelector(
    (state) => state["users_management"],
  );
  // read the fetchParams from the redux store to
  // preserve state upon websocket-based updates
  const fetchParams = useAppSelector(
    (state) => state["users_management"].fetchParams,
  );
  const [tableFilterList, setTableFilterList] = useState<string[]>([]);
  const streams = useAppSelector((state) => state["streams"]);
  let { all: allGroups } = useAppSelector((state) => state.groups);
  const { data: acls } = useGetAclsQuery();
  const [addUserAcls] = useAddUserAclsMutation();
  const [deleteUserAcl] = useDeleteUserAclMutation();
  const roles = useAppSelector((state) => state["roles"]);
  const [addUserGroupsDialogOpen, setAddUserGroupsDialogOpen] = useState(false);
  const [addUserRolesDialogOpen, setAddUserRolesDialogOpen] = useState(false);
  const [addUserACLsDialogOpen, setAddUserACLsDialogOpen] = useState(false);
  const [addUserAffiliationsDialogOpen, setAddUserAffiliationsDialogOpen] =
    useState(false);
  const [addUserStreamsDialogOpen, setAddUserStreamsDialogOpen] =
    useState(false);
  const [
    editUserExpirationDateDialogOpen,
    setEditUserExpirationDateDialogOpen,
  ] = useState(false);
  const [
    removeExpirationConfirmDialogOpen,
    setRemoveExpirationConfirmDialogOpen,
  ] = useState(false);
  const [clickedUser, setClickedUser] = useState<any>(null);
  const [dataFetched, setDataFetched] = useState(false);

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  const filter = createFilterOptions();

  useEffect(() => {
    const fetchData = () => {
      dispatch(
        setUsersManagementFetchParams({
          pageNumber: 1,
          numPerPage: 25,
          ...fetchParams,
        }),
      );
      dispatch(fetchUsersManagement());
      dispatch(streamsActions.fetchStreams());
      dispatch(rolesActions.fetchRoles());
      dispatch(invitationsActions.fetchInvitations());
    };
    if (!dataFetched) {
      fetchData();
      setDataFetched(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataFetched, dispatch]);

  const handleFilterSubmit = async (formData: any) => {
    setQueryInProgress(true);
    Object.keys(formData).forEach(
      (key) => !formData[key] && delete formData[key],
    );
    setTableFilterList(
      Object.entries(formData).map(([key, value]) => `${key}: ${value}`),
    );
    const params = {
      ...formData,
      pageNumber: 1,
      numPerPage: rowsPerPage,
      includeExpired: fetchParams.includeExpired || false,
    };
    dispatch(setUsersManagementFetchParams(params));
    await dispatch(fetchUsersManagement());
    setQueryInProgress(false);
    // Close the filter dialog after applying the filter. Otherwise the dialog
    // (and its own "Submit" button) stays mounted, which both blocks the table
    // underneath and causes the unscoped `//*[text()="Submit"]` selectors used
    // by the action dialogs to match the leftover filter Submit instead.
    setFilterOpen(false);
  };

  const handleFilterChipDelete = (chip: string) => {
    const remaining = tableFilterList.filter((c) => c !== chip);
    // Convert remaining chip filter list to filter form data
    const data: any = {};
    remaining.forEach((filterChip) => {
      const [key, value] = filterChip.split(": ");
      if (key) {
        data[key] = value;
      }
    });
    handleFilterSubmit(data);
  };

  const handleToggleExpiredUsers = async (event: any) => {
    const newValue = event.target.checked;
    dispatch(
      setUsersManagementFetchParams({
        ...fetchParams,
        includeExpired: newValue,
      }),
    );
    setQueryInProgress(true);
    await dispatch(fetchUsersManagement());
    setQueryInProgress(false);
  };

  // Memoize the toolbar so it keeps a stable component identity across the
  // re-renders triggered by server-side data loading. Without this, the inline
  // function identity changes every render, forcing MUI to unmount/remount the
  // toolbar (and its filter button) and invalidating any element references a
  // test is mid-interaction with (StaleElementReferenceException). Declared
  // before the early return so the hook runs on every render (rules-of-hooks).
  const CustomToolbar = useMemo(
    () =>
      function UserManagementToolbar() {
        return (
          <GridToolbarContainer>
            <GridToolbarColumnsButton />
            <Tooltip title="Filter Table">
              <IconButton
                size="small"
                data-testid="Filter Table-iconButton"
                onClick={() => setFilterOpen(true)}
              >
                <FilterListIcon />
              </IconButton>
            </Tooltip>
            <FormControlLabel
              control={
                <Switch
                  checked={fetchParams.includeExpired || false}
                  onChange={handleToggleExpiredUsers}
                  color="primary"
                  data-testid="showExpiredUsersToggle"
                />
              }
              label="Show Expired Users"
              style={{ marginRight: "1rem" }}
            />
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
      },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fetchParams.includeExpired, tableFilterList],
  );

  if (
    !currentUser?.username?.length ||
    !allGroups?.length ||
    streams === null ||
    !acls?.length ||
    !roles?.length
  ) {
    return <Spinner />;
  }

  if (
    !(
      currentUser.permissions?.includes("System admin") ||
      currentUser.permissions?.includes("Manage users")
    )
  ) {
    return <div>Access denied: Insufficient permissions.</div>;
  }
  allGroups = allGroups?.filter((group) => !group.single_user_group);

  const validateGroups = () => {
    const formState = getValues();
    return formState["groups"].length >= 1;
  };

  const validateStreams = () => {
    const formState = getValues();
    return formState["streams"].length >= 1;
  };

  const validateACLs = () => {
    const formState = getValues();
    return formState["acls"].length >= 1;
  };

  const validateRoles = () => {
    const formState = getValues();
    return formState["roles"].length >= 1;
  };

  const handleAddUserToGroups = async (formData: any) => {
    const groupIDs = formData.groups?.map((g: any) => g.id);
    const promises = groupIDs?.map((gid: any) =>
      dispatch(
        groupsActions.addGroupUser({
          userID: clickedUser.id,
          admin: false,
          group_id: gid,
        } as any),
      ),
    );
    const results: any[] = await Promise.all(promises);
    if (results.every((result: any) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified group(s)."),
      );
      reset({ groups: [] });
      setAddUserGroupsDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
    }
  };

  const handleAddUserToStreams = async (formData: any) => {
    const streamIDs = formData.streams?.map((g: any) => g.id);
    const promises = streamIDs?.map((sid: any) =>
      dispatch(
        streamsActions.addStreamUser({
          user_id: clickedUser.id,
          stream_id: sid,
        }),
      ),
    );
    const results: any[] = await Promise.all(promises);
    if (results.every((result: any) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified stream(s)."),
      );
      reset({ streams: [] });
      setAddUserStreamsDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
    }
  };

  const handleAddUserACLs = async (formData: any) => {
    try {
      await addUserAcls({
        userID: clickedUser.id,
        aclIds: formData.acls,
      }).unwrap();
      dispatch(showNotification("User successfully granted specified ACL(s)."));
      reset({ acls: [] });
      setAddUserACLsDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
    } catch {
      // error notification handled centrally by the base query
    }
  };

  const handleAddUserAffiliations = async (formData: any) => {
    const result: any = await dispatch(
      ProfileActions.updateBasicUserInfo(formData, clickedUser.id),
    );
    if (result.status === "success") {
      dispatch(showNotification("Successfully updated user's affiliations."));
      setAddUserAffiliationsDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
    }
  };

  const handleAddUserRoles = async (formData: any) => {
    const result: any = await dispatch(
      rolesActions.addUserRoles({
        userID: clickedUser.id,
        roleIds: formData.roles?.map((role: any) => role.id),
      }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully granted specified role(s)."),
      );
      reset({ roles: [] });
      setAddUserRolesDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
    }
  };

  const handleClickRemoveUserFromGroup = async (userID: any, group_id: any) => {
    const result: any = await dispatch(
      groupsActions.deleteGroupUser({ userID, group_id }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully removed from specified group."),
      );
      await dispatch(fetchUsersManagement());
    }
  };

  const handleClickRemoveUserStreamAccess = async (
    user_id: any,
    stream_id: any,
  ) => {
    const result: any = await dispatch(
      streamsActions.deleteStreamUser({ user_id, stream_id }),
    );
    if (result.status === "success") {
      dispatch(showNotification("Stream access successfully revoked."));
      await dispatch(fetchUsersManagement());
    }
  };

  const handleClickDeleteUserACL = async (userID: any, acl: any) => {
    try {
      await deleteUserAcl({ userID, acl }).unwrap();
      dispatch(showNotification("User ACL successfully removed."));
      await dispatch(fetchUsersManagement());
    } catch {
      // error notification handled centrally by the base query
    }
  };

  const handleClickDeleteUserAffiliations = async (
    user: any,
    affiliation: any,
  ) => {
    const data = {
      affiliations: user.affiliations.filter(
        (value: any) => value !== affiliation,
      ),
    };
    const result: any = await dispatch(
      ProfileActions.updateBasicUserInfo(data, user.id),
    );
    if (result.status === "success") {
      dispatch(showNotification("Successfully deleted user's affiliation."));
      await dispatch(fetchUsersManagement());
    }
  };

  const handleClickDeleteUserRole = async (userID: any, role: any) => {
    const result: any = await dispatch(
      rolesActions.deleteUserRole({ userID, role }),
    );
    if (result.status === "success") {
      dispatch(showNotification("User role successfully removed."));
      await dispatch(fetchUsersManagement());
    }
  };

  const handleRemoveUserExpirationDate = async () => {
    const result: any = await dispatch(
      patchUser(clickedUser.id, {
        expirationDate: null,
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification("User expiration date successfully removed."));
      reset({ date: null });
      setEditUserExpirationDateDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
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
    const result: any = await dispatch(
      patchUser(clickedUser.id, {
        expirationDate: dayjs.utc(formData.date).toISOString(),
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification("User expiration date successfully updated."));
      reset({ date: null });
      setEditUserExpirationDateDialogOpen(false);
      await dispatch(fetchUsersManagement());
      setClickedUser(null);
    }
  };

  // DataGrid cell renderers
  const renderName = (params: any) => {
    const user = params.row;
    return (
      <div>
        {`${user.first_name ? user.first_name : ""}`}
        <UpdateUserParameter user={user} parameter="first_name" />
        {`${user.last_name ? user.last_name : ""}`}
        <UpdateUserParameter user={user} parameter="last_name" />
      </div>
    );
  };

  const renderUsername = (params: any) => {
    const user = params.row;
    return (
      <div>
        {`${user.username}`}
        <UpdateUserParameter user={user} parameter="username" />
      </div>
    );
  };

  const renderEmail = (params: any) => {
    const user = params.row;
    return (
      <div>
        {`${user.contact_email ? user.contact_email : ""}`}
        <UpdateUserParameter user={user} parameter="contact_email" />
      </div>
    );
  };

  const renderRoles = (params: any) => {
    const user = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-role"
          data-testid={`addUserRolesButton${user.id}`}
          onClick={() => {
            setClickedUser(user);
            setAddUserRolesDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {user?.roles?.map((role: any) => (
          <Chip
            label={role}
            onDelete={() => {
              handleClickDeleteUserRole(user.id, role);
            }}
            key={role}
            data-testid={`deleteUserRoleButton_${user.id}_${role}`}
          />
        ))}
      </div>
    );
  };

  const renderRolesHeader = () => (
    <div style={{ display: "flex", alignItems: "center" }}>
      Roles
      <Tooltip
        title={
          <>
            <b>Each role is associated with the following ACLs:</b>
            <ul>
              {roles?.map((role: any) => (
                <li key={role.id}>
                  {role.id}: {role.acls.join(", ")}
                </li>
              ))}
            </ul>
          </>
        }
      >
        <HelpIcon color="disabled" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const renderACLs = (params: any) => {
    const user = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-acl"
          data-testid={`addUserACLsButton${user.id}`}
          onClick={() => {
            setClickedUser(user);
            setAddUserACLsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {user?.acls?.map((acl: any) => (
          <Chip
            label={acl}
            onDelete={() => {
              handleClickDeleteUserACL(user.id, acl);
            }}
            key={acl}
            data-testid={`deleteUserACLButton_${user.id}_${acl}`}
          />
        ))}
      </div>
    );
  };

  const renderACLsHeader = () => (
    <div style={{ display: "flex", alignItems: "center" }}>
      ACLs
      <Tooltip
        title={
          <>
            <p>
              These are in addition to those ACLs associated with user role(s).
              See help icon tooltip in roles column header for those ACLs.
            </p>
          </>
        }
      >
        <HelpIcon color="disabled" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const renderAffiliations = (params: any) => {
    const user = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-affiliation"
          data-testid={`addUserAffiliationsButton${user.id}`}
          onClick={() => {
            setClickedUser(user);
            setAddUserAffiliationsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {user?.affiliations?.map((affiliation: any) => (
          <Chip
            label={affiliation}
            onDelete={() => {
              handleClickDeleteUserAffiliations(user, affiliation);
            }}
            key={affiliation}
            data-testid={`deleteUserAffiliationsButton_${user.id}_${affiliation}`}
          />
        ))}
      </div>
    );
  };

  const renderAffiliationsHeader = () => (
    <div style={{ display: "flex", alignItems: "center" }}>
      Affiliations
      <Tooltip
        title={
          <>
            <p>
              These are affiliations. They can be used when writing papers or
              circulars
            </p>
          </>
        }
      >
        <HelpIcon color="disabled" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const renderGroups = (params: any) => {
    const user = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-group"
          data-testid={`addUserGroupsButton${user.id}`}
          onClick={() => {
            setClickedUser(user);
            setAddUserGroupsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {user.groups
          ?.filter((group: any) => !group.single_user_group)
          ?.map((group: any) => (
            <Chip
              label={group.name}
              onDelete={() => {
                handleClickRemoveUserFromGroup(user.id, group.id);
              }}
              key={group.id}
              data-testid={`deleteGroupUserButton_${user.id}_${group.id}`}
            />
          ))}
      </div>
    );
  };

  const renderStreams = (params: any) => {
    const user = params.row;
    return (
      <div>
        <IconButton
          aria-label="add-stream"
          data-testid={`addUserStreamsButton${user.id}`}
          onClick={() => {
            setClickedUser(user);
            setAddUserStreamsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {user.streams?.map((stream: any) => (
          <Chip
            label={stream.name}
            onDelete={() => {
              handleClickRemoveUserStreamAccess(user.id, stream.id);
            }}
            key={stream.id}
            data-testid={`deleteStreamUserButton_${user.id}_${stream.id}`}
          />
        ))}
      </div>
    );
  };

  const renderExpirationDate = (params: any) => {
    const user = params.row;
    const isExpired = dayjs.utc().isAfter(user.expiration_date);
    return (
      <div className={isExpired ? classes.expired : ""}>
        {user.expiration_date
          ? dayjs.utc(user.expiration_date).format("YYYY/MM/DD")
          : ""}
        <IconButton
          aria-label="edit-expiration"
          data-testid={`editUserExpirationDate${user.id}`}
          onClick={() => {
            setClickedUser(user);
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

  const handlePageChange = async (page: number, numPerPage: number) => {
    setQueryInProgress(true);
    const params = { ...fetchParams, numPerPage, pageNumber: page + 1 };
    // Save state for future
    dispatch(setUsersManagementFetchParams(params));
    await dispatch(fetchUsersManagement());
    setQueryInProgress(false);
  };

  const handleUserTableSorting = async (sortData: any) => {
    setQueryInProgress(true);
    const sortBy = sortData.name === "created_at" ? "createdAt" : "username";
    const sortOrder = sortData.direction;
    const params = {
      ...fetchParams,
      pageNumber: 1,
      sortBy,
      sortOrder,
    };
    dispatch(setUsersManagementFetchParams(params));
    await dispatch(fetchUsersManagement());
    setQueryInProgress(false);
  };

  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    handlePageChange(model.page, model.pageSize);
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    if (!model.length) {
      handleUserTableSorting({ name: "username", direction: "asc" });
      return;
    }
    const { field, sort } = model[0];
    handleUserTableSorting({
      name: SERVER_SORT_FIELD[field] || field,
      direction: sort,
    });
  };

  const customFilterDisplay = () => {
    // Assemble json form schema for possible server-side filtering values
    const filterFormSchema = {
      type: "object",
      properties: {
        firstName: {
          type: "string",
          title: "First name",
        },
        lastName: {
          type: "string",
          title: "Last name",
        },
        username: {
          type: "string",
          title: "Username",
        },
        affiliations: {
          type: "string",
          title: "Affiliations",
        },
        email: {
          type: "string",
          title: "Email",
        },
        role: {
          title: "Role",
          type: "string",
          enum: roles?.map((role: any) => role.id),
        },
        acl: {
          title: "Additional ACL",
          type: "string",
          enum: acls,
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
      field: "first_name",
      headerName: "Name",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderName,
    },
    {
      field: "username",
      headerName: "Username",
      flex: 1,
      minWidth: 130,
      filterable: false,
      renderCell: renderUsername,
    },
    {
      field: "created_at",
      headerName: "Created At",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: (params: any) => {
        const user = params.row;
        return user.created_at
          ? dayjs.utc(user.created_at).format("YYYY/MM/DD")
          : "";
      },
    },
    {
      field: "affiliations",
      headerName: "Affiliations",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderHeader: renderAffiliationsHeader,
      renderCell: renderAffiliations,
    },
    {
      field: "contact_email",
      headerName: "Email",
      flex: 1,
      minWidth: 180,
      sortable: false,
      filterable: false,
      renderCell: renderEmail,
    },
    {
      field: "roles",
      headerName: "Roles",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderHeader: renderRolesHeader,
      renderCell: renderRoles,
    },
    {
      field: "addition",
      headerName: "Additional ACLS",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderHeader: renderACLsHeader,
      renderCell: renderACLs,
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
      field: "expiration_date",
      headerName: "Expiration Date",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderHeader: renderExpirationDateHeader,
      renderCell: renderExpirationDate,
    },
  ];

  return (
    <>
      <Paper>
        <Typography variant="h6" style={{ padding: "0.5rem 0.75rem 0" }}>
          Manage Users
        </Typography>
        <Box sx={{ height: "calc(100vh - 201px)", width: "100%" }}>
          <StyledDataGrid
            columns={columns}
            rows={users || []}
            getRowId={(row: any) => row.id}
            loading={queryInProgress}
            paginationMode="server"
            sortingMode="server"
            rowCount={totalMatches}
            paginationModel={{
              page: (fetchParams.pageNumber || 1) - 1,
              pageSize: rowsPerPage,
            }}
            onPaginationModelChange={handlePaginationModelChange}
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            disableColumnFilter
            // Keep all columns mounted so the action buttons in the rightmost
            // columns (streams, expiration date, etc.) render even when they
            // would otherwise be virtualized out of the horizontal viewport.
            columnBufferPx={3000}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
      </Paper>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>{customFilterDisplay()}</DialogContent>
      </Dialog>
      {invitationsEnabled && (
        <div style={{ marginTop: "1rem" }}>
          <UserInvitations />
        </div>
      )}
      <Dialog
        open={addUserGroupsDialogOpen}
        onClose={() => setAddUserGroupsDialogOpen(false)}
      >
        <DialogTitle>{`Add user ${clickedUser?.username} to selected groups:`}</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserToGroups)}>
            {!!errors["groups"] && (
              <FormValidationError message="Please select at least one group" />
            )}
            <Controller
              name="groups"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(_e, data) => onChange(data)}
                  value={value}
                  options={allGroups?.filter(
                    (g) =>
                      !clickedUser?.groups
                        ?.map((gr: any) => gr.id)
                        ?.includes(g.id),
                  )}
                  getOptionLabel={(group: any) => group.name}
                  filterSelectedOptions
                  data-testid="addUserToGroupsSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      error={!!errors["groups"]}
                      variant="outlined"
                      label="Select Groups"
                      data-testid="addUserToGroupsTextField"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateGroups }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddFromGroupsButton"
                data-testid="submitAddFromGroupsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={addUserStreamsDialogOpen}
        onClose={() => setAddUserStreamsDialogOpen(false)}
      >
        <DialogTitle>
          {`Grant user ${clickedUser?.username} access to selected streams:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserToStreams)}>
            {!!errors["streams"] && (
              <FormValidationError message="Please select at least one stream" />
            )}
            <Controller
              name="streams"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(_e, data) => onChange(data)}
                  value={value}
                  options={streams?.filter(
                    (s: any) =>
                      !clickedUser?.streams
                        ?.map((strm: any) => strm.id)
                        ?.includes(s.id),
                  )}
                  getOptionLabel={(stream: any) => stream.name}
                  filterSelectedOptions
                  data-testid="addUserToStreamsSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      error={!!errors["streams"]}
                      variant="outlined"
                      label="Select Streams"
                      data-testid="addUserToStreamsTextField"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateStreams }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddStreamsButton"
                data-testid="submitAddStreamsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={addUserACLsDialogOpen}
        onClose={() => setAddUserACLsDialogOpen(false)}
      >
        <DialogTitle>
          {`Grant user ${clickedUser?.username} selected ACLs:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserACLs)}>
            {!!errors["acls"] && (
              <FormValidationError message="Please select at least one ACL" />
            )}
            <Controller
              name="acls"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(_e, data) => onChange(data)}
                  value={value}
                  options={acls?.filter(
                    (acl: any) => !clickedUser?.permissions?.includes(acl),
                  )}
                  getOptionLabel={(acl: any) => acl}
                  filterSelectedOptions
                  data-testid="addUserACLsSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      error={!!errors["acls"]}
                      variant="outlined"
                      label="Select ACLs"
                      data-testid="addUserACLsTextField"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateACLs }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddACLsButton"
                data-testid="submitAddACLsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={addUserAffiliationsDialogOpen}
        onClose={() => setAddUserAffiliationsDialogOpen(false)}
      >
        <DialogTitle>
          {`Update user ${clickedUser?.username} affiliations:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserAffiliations)}>
            <Controller
              name="affiliations"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(_e, data) => onChange(data)}
                  value={value}
                  options={clickedUser?.affiliations?.map((aff: any) => aff)}
                  filterOptions={(options, params) => {
                    const filtered = filter(options, params);

                    const { inputValue } = params;
                    // Suggest the creation of a new value
                    const isExisting = options.some(
                      (option: any) => inputValue === option,
                    );
                    if (inputValue !== "" && !isExisting) {
                      filtered.push(inputValue);
                    }

                    return filtered;
                  }}
                  getOptionLabel={(option: any) => {
                    // Value selected with enter, right from the input
                    if (typeof option === "string") {
                      return option;
                    }
                    // Add "xxx" option created dynamically
                    if (option.inputValue) {
                      return option.inputValue;
                    }
                    // Regular option
                    return option;
                  }}
                  freeSolo
                  data-testid="addUserAffiliationsSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      variant="outlined"
                      label="Select Affiliations"
                      data-testid="addUserAffiliationsTextField"
                    />
                  )}
                />
              )}
              control={control}
              defaultValue={clickedUser?.affiliations}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddAffiliationsButton"
                data-testid="submitAddAffilitiationsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={addUserRolesDialogOpen}
        onClose={() => setAddUserRolesDialogOpen(false)}
      >
        <DialogTitle>
          {`Grant user ${clickedUser?.username} selected roles:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserRoles)}>
            {!!errors["roles"] && (
              <FormValidationError message="Please select at least one role" />
            )}
            <Controller
              name="roles"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(_e, data) => onChange(data)}
                  value={value}
                  options={roles?.filter(
                    (role: any) => !clickedUser?.roles?.includes(role.id),
                  )}
                  sx={{ mt: 1 }}
                  getOptionLabel={(role: any) => role.id}
                  filterSelectedOptions
                  data-testid="addUserRolesSelect"
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      error={!!errors["roles"]}
                      variant="outlined"
                      label="Select Roles"
                    />
                  )}
                />
              )}
              control={control}
              rules={{ validate: validateRoles }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                primary
                type="submit"
                name="submitAddRolesButton"
                data-testid="submitAddRolesButton"
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
        <DialogTitle>
          {`Edit user ${clickedUser?.username} expiration date:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleEditUserExpirationDate)}>
            <Controller
              render={({ field: { onChange, value } }) => (
                <LocalizationProvider dateAdapter={AdapterDateFns}>
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
                </LocalizationProvider>
              )}
              name="date"
              control={control}
              defaultValue={null}
            />
            <br />
            <div
              className={classes.submitButton}
              style={{ display: "flex", gap: "0.5rem" }}
            >
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
                  setRemoveExpirationConfirmDialogOpen(true);
                }}
                name="removeExpirationDateButton"
                data-testid="removeExpirationDateButton"
              >
                Remove Expiration Date
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={removeExpirationConfirmDialogOpen}
        onClose={() => setRemoveExpirationConfirmDialogOpen(false)}
      >
        <DialogTitle>Confirm Removal</DialogTitle>
        <DialogContent>
          <p>
            Are you sure you want to remove the expiration date for user{" "}
            <strong>{clickedUser?.username}</strong>? This will reactivate their
            account.
          </p>
          <div
            className={classes.submitButton}
            style={{ display: "flex", gap: "0.5rem" }}
          >
            <Button
              primary
              onClick={() => {
                handleRemoveUserExpirationDate();
                setRemoveExpirationConfirmDialogOpen(false);
                setEditUserExpirationDateDialogOpen(false);
              }}
              name="confirmRemoveExpirationButton"
              data-testid="confirmRemoveExpirationButton"
            >
              Yes, Remove Expiration Date
            </Button>
            <Button
              secondary
              onClick={() => setRemoveExpirationConfirmDialogOpen(false)}
              name="cancelRemoveExpirationButton"
              data-testid="cancelRemoveExpirationButton"
            >
              Cancel
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UserManagement;

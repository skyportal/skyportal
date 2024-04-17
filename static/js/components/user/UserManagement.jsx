import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";

import MUIDataTable from "mui-datatables";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import HelpIcon from "@mui/icons-material/Help";
import EditIcon from "@mui/icons-material/Edit";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import FormValidationError from "../FormValidationError";
import UserInvitations from "./UserInvitations";
import UpdateUserParameter from "../UpdateUserParameter";
import * as groupsActions from "../../ducks/groups";
import * as usersActions from "../../ducks/users";
import * as streamsActions from "../../ducks/streams";
import * as invitationsActions from "../../ducks/invitations";
import * as aclsActions from "../../ducks/acls";
import * as rolesActions from "../../ducks/roles";
import Spinner from "../Spinner";

import * as ProfileActions from "../../ducks/profile";

dayjs.extend(utc);

const useStyles = makeStyles(() => ({
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
  expired: {
    color: "red",
  },
}));

const dataTableStyles = (theme) =>
  createTheme({
    overrides: {
      MuiPaper: {
        elevation4: {
          boxShadow: "none !important",
        },
      },
    },
    palette: theme.palette,
  });

const defaultNumPerPage = 25;

const UserManagement = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const [rowsPerPage, setRowsPerPage] = useState(defaultNumPerPage);
  const [queryInProgress, setQueryInProgress] = useState(false);
  const { invitationsEnabled } = useSelector((state) => state.config);
  const currentUser = useSelector((state) => state.profile);
  const { users, totalMatches } = useSelector((state) => state.users);
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });
  const [tableFilterList, setTableFilterList] = useState([]);
  const streams = useSelector((state) => state.streams);
  let { all: allGroups } = useSelector((state) => state.groups);
  const acls = useSelector((state) => state.acls);
  const roles = useSelector((state) => state.roles);
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
  const [clickedUser, setClickedUser] = useState(null);
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
      dispatch(usersActions.fetchUsers(fetchParams));
      dispatch(streamsActions.fetchStreams());
      dispatch(aclsActions.fetchACLs());
      dispatch(rolesActions.fetchRoles());
      dispatch(invitationsActions.fetchInvitations());
    };
    if (!dataFetched) {
      fetchData();
      setDataFetched(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataFetched, dispatch]);

  if (
    !currentUser?.username?.length ||
    !allGroups?.length ||
    !streams?.length ||
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
    return formState.groups.length >= 1;
  };

  const validateStreams = () => {
    const formState = getValues();
    return formState.streams.length >= 1;
  };

  const validateACLs = () => {
    const formState = getValues();
    return formState.acls.length >= 1;
  };

  const validateRoles = () => {
    const formState = getValues();
    return formState.roles.length >= 1;
  };

  const handleAddUserToGroups = async (formData) => {
    const groupIDs = formData.groups?.map((g) => g.id);
    const promises = groupIDs?.map((gid) =>
      dispatch(
        groupsActions.addGroupUser({
          userID: clickedUser.id,
          admin: false,
          group_id: gid,
        }),
      ),
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified group(s)."),
      );
      reset({ groups: [] });
      setAddUserGroupsDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleAddUserToStreams = async (formData) => {
    const streamIDs = formData.streams?.map((g) => g.id);
    const promises = streamIDs?.map((sid) =>
      dispatch(
        streamsActions.addStreamUser({
          user_id: clickedUser.id,
          stream_id: sid,
        }),
      ),
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified stream(s)."),
      );
      reset({ streams: [] });
      setAddUserStreamsDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleAddUserACLs = async (formData) => {
    const result = await dispatch(
      aclsActions.addUserACLs({
        userID: clickedUser.id,
        aclIds: formData.acls,
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification("User successfully granted specified ACL(s)."));
      reset({ acls: [] });
      setAddUserACLsDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleAddUserAffiliations = async (formData) => {
    const result = await dispatch(
      ProfileActions.updateBasicUserInfo(formData, clickedUser.id),
    );
    if (result.status === "success") {
      dispatch(showNotification("Successfully updated user's affiliations."));
      setAddUserAffiliationsDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleAddUserRoles = async (formData) => {
    const result = await dispatch(
      rolesActions.addUserRoles({
        userID: clickedUser.id,
        roleIds: formData.roles?.map((role) => role.id),
      }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully granted specified role(s)."),
      );
      reset({ roles: [] });
      setAddUserRolesDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleClickRemoveUserFromGroup = async (userID, group_id) => {
    const result = await dispatch(
      groupsActions.deleteGroupUser({ userID, group_id }),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully removed from specified group."),
      );
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  const handleClickRemoveUserStreamAccess = async (user_id, stream_id) => {
    const result = await dispatch(
      streamsActions.deleteStreamUser({ user_id, stream_id }),
    );
    if (result.status === "success") {
      dispatch(showNotification("Stream access successfully revoked."));
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  const handleClickDeleteUserACL = async (userID, acl) => {
    const result = await dispatch(aclsActions.deleteUserACL({ userID, acl }));
    if (result.status === "success") {
      dispatch(showNotification("User ACL successfully removed."));
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  const handleClickDeleteUserAffiliations = async (user, affiliation) => {
    const data = {
      affiliations: user.affiliations.filter((value) => value !== affiliation),
    };
    const result = await dispatch(
      ProfileActions.updateBasicUserInfo(data, user.id),
    );
    if (result.status === "success") {
      dispatch(showNotification("Successfully deleted user's affiliation."));
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  const handleClickDeleteUserRole = async (userID, role) => {
    const result = await dispatch(
      rolesActions.deleteUserRole({ userID, role }),
    );
    if (result.status === "success") {
      dispatch(showNotification("User role successfully removed."));
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  const handleEditUserExpirationDate = async (formData) => {
    if (!dayjs.utc(formData.date).isValid()) {
      dispatch(
        showNotification(
          "Invalid date. Please use MM/DD/YYYY format.",
          "error",
        ),
      );
      return;
    }
    const result = await dispatch(
      usersActions.patchUser(clickedUser.id, {
        expirationDate: dayjs.utc(formData.date).toISOString(),
      }),
    );
    if (result.status === "success") {
      dispatch(showNotification("User expiration date successfully updated."));
      reset({ date: null });
      setEditUserExpirationDateDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  // MUI DataTable functions
  const renderName = (dataIndex) => {
    const user = users[dataIndex];
    return (
      <div>
        {`${user.first_name ? user.first_name : ""}`}
        <UpdateUserParameter user={user} parameter="first_name" />
        {`${user.last_name ? user.last_name : ""}`}
        <UpdateUserParameter user={user} parameter="last_name" />
      </div>
    );
  };

  // MUI DataTable functions
  const renderUsername = (dataIndex) => {
    const user = users[dataIndex];
    return (
      <div>
        {`${user.username}`}
        <UpdateUserParameter user={user} parameter="username" />
      </div>
    );
  };

  const renderEmail = (dataIndex) => {
    const user = users[dataIndex];
    return (
      <div>
        {`${user.contact_email ? user.contact_email : ""}`}
        <UpdateUserParameter user={user} parameter="contact_email" />
      </div>
    );
  };

  const renderRoles = (dataIndex) => {
    const user = users[dataIndex];
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
        {user?.roles?.map((role) => (
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
              {roles?.map((role) => (
                <li key={role.id}>
                  {role.id}: {role.acls.join(", ")}
                </li>
              ))}
            </ul>
          </>
        }
      >
        <HelpIcon color="disabled" size="small" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const renderACLs = (dataIndex) => {
    const user = users[dataIndex];
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
        {user?.acls?.map((acl) => (
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
        <HelpIcon color="disabled" size="small" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const renderAffiliations = (dataIndex) => {
    const user = users[dataIndex];
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
        {user?.affiliations?.map((affiliation) => (
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
        <HelpIcon color="disabled" size="small" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const renderGroups = (dataIndex) => {
    const user = users[dataIndex];
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
          ?.filter((group) => !group.single_user_group)
          ?.map((group) => (
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

  const renderStreams = (dataIndex) => {
    const user = users[dataIndex];
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
        {user.streams?.map((stream) => (
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

  const renderExpirationDate = (dataIndex) => {
    const user = users[dataIndex];
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
        <HelpIcon color="disabled" size="small" className={classes.icon} />
      </Tooltip>
    </div>
  );

  const handleFilterSubmit = async (formData) => {
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
    await dispatch(usersActions.fetchUsers(params));
    setQueryInProgress(false);
  };

  const handleTableFilterChipChange = (column, filterList, type) => {
    if (type === "chip") {
      const nameFilterList = filterList[0];
      // Convert chip filter list to filter form data
      const data = {};
      nameFilterList.forEach((filterChip) => {
        const [key, value] = filterChip.split(": ");
        data[key] = value;
      });
      handleFilterSubmit(data);
    }
  };

  const handlePageChange = async (page, numPerPage) => {
    setQueryInProgress(true);
    const params = { ...fetchParams, numPerPage, pageNumber: page + 1 };
    // Save state for future
    setFetchParams(params);
    await dispatch(usersActions.fetchUsers(params));
    setQueryInProgress(false);
  };

  const handleTableChange = (action, tableState) => {
    setRowsPerPage(tableState.rowsPerPage);
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        handlePageChange(tableState.page, tableState.rowsPerPage);
        break;
      default:
    }
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
          enum: roles?.map((role) => role.id),
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
          enum: streams?.map((stream) => stream.name),
        },
      },
    };

    return !queryInProgress ? (
      <div>
        <Form
          schema={filterFormSchema}
          validator={validator}
          onSubmit={({ formData }) => {
            handleFilterSubmit(formData);
          }}
        />
      </div>
    ) : (
      <div />
    );
  };

  const columns = [
    {
      name: "first_name",
      label: "Name",
      options: {
        customBodyRenderLite: renderName,
        // Hijack custom filtering for this column to use for the entire form
        // Individually using custom filter renders on each column led to issues
        // with the form RESET button not being hooked up properly when combined
        // with server-side pagination/filter confirmation
        filter: !queryInProgress,
        filterType: "custom",
        filterList: tableFilterList,
        filterOptions: {
          // eslint-disable-next-line react/display-name
          display: () => <div />,
        },
      },
    },
    {
      name: "username",
      label: "Username",
      options: {
        // Turn off default filtering for custom form
        filter: false,
        customBodyRenderLite: renderUsername,
      },
    },
    {
      name: "affiliations",
      label: "Affiliations",
      options: {
        sort: false,
        customBodyRenderLite: renderAffiliations,
        customHeadLabelRender: renderAffiliationsHeader,
        filter: false,
      },
    },
    {
      name: "contact_email",
      label: "Email",
      options: {
        filter: false,
        customBodyRenderLite: renderEmail,
      },
    },
    {
      name: "roles",
      label: "Roles",
      options: {
        sort: false,
        customBodyRenderLite: renderRoles,
        customHeadLabelRender: renderRolesHeader,
        filter: false,
      },
    },
    {
      name: "addition",
      label: "Additional ACLS",
      options: {
        sort: false,
        customBodyRenderLite: renderACLs,
        customHeadLabelRender: renderACLsHeader,
        filter: false,
      },
    },
    {
      name: "groups",
      label: "Groups",
      options: {
        sort: false,
        customBodyRenderLite: renderGroups,
        filter: false,
      },
    },
    {
      name: "streams",
      label: "Streams",
      options: {
        sort: false,
        customBodyRenderLite: renderStreams,
        filter: false,
      },
    },
    {
      name: "expiration_date",
      label: "Expiration Date",
      options: {
        sort: false,
        filter: false,
        customBodyRenderLite: renderExpirationDate,
        customHeadLabelRender: renderExpirationDateHeader,
      },
    },
  ];

  const options = {
    responsive: "standard",
    print: true,
    download: true,
    search: false,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    sort: false,
    rowsPerPage,
    rowsPerPageOptions: [10, 25, 50, 100, 200],
    filter: !queryInProgress,
    customFilterDialogFooter: customFilterDisplay,
    onFilterChange: handleTableFilterChipChange,
    jumpToPage: true,
    serverSide: true,
    pagination: true,
    rowHover: false,
    count: totalMatches,
    onTableChange: handleTableChange,
  };

  return (
    <Paper className={classes.container}>
      <Typography variant="h5">Manage users</Typography>
      <Paper className={classes.section}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={dataTableStyles(theme)}>
            <MUIDataTable columns={columns} data={users} options={options} />
          </ThemeProvider>
        </StyledEngineProvider>
      </Paper>
      <br />
      {invitationsEnabled && <UserInvitations />}
      <Dialog
        open={addUserGroupsDialogOpen}
        onClose={() => {
          setAddUserGroupsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>{`Add user ${clickedUser?.username} to selected groups:`}</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserToGroups)}>
            {!!errors.groups && (
              <FormValidationError message="Please select at least one group" />
            )}
            <Controller
              name="groups"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(e, data) => onChange(data)}
                  value={value}
                  options={allGroups?.filter(
                    (g) =>
                      !clickedUser?.groups?.map((gr) => gr.id)?.includes(g.id),
                  )}
                  getOptionLabel={(group) => group.name}
                  filterSelectedOptions
                  data-testid="addUserToGroupsSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.groups}
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
        onClose={() => {
          setAddUserStreamsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>
          {`Grant user ${clickedUser?.username} access to selected streams:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserToStreams)}>
            {!!errors.streams && (
              <FormValidationError message="Please select at least one stream" />
            )}
            <Controller
              name="streams"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(e, data) => onChange(data)}
                  value={value}
                  options={streams?.filter(
                    (s) =>
                      !clickedUser?.streams
                        ?.map((strm) => strm.id)
                        ?.includes(s.id),
                  )}
                  getOptionLabel={(stream) => stream.name}
                  filterSelectedOptions
                  data-testid="addUserToStreamsSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.streams}
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
        onClose={() => {
          setAddUserACLsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>
          {`Grant user ${clickedUser?.username} selected ACLs:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserACLs)}>
            {!!errors.acls && (
              <FormValidationError message="Please select at least one ACL" />
            )}
            <Controller
              name="acls"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(e, data) => onChange(data)}
                  value={value}
                  options={acls?.filter(
                    (acl) => !clickedUser?.permissions?.includes(acl),
                  )}
                  getOptionLabel={(acl) => acl}
                  filterSelectedOptions
                  data-testid="addUserACLsSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.acls}
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
        onClose={() => {
          setAddUserAffiliationsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
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
                  onChange={(e, data) => onChange(data)}
                  value={value}
                  options={clickedUser?.affiliations?.map((aff) => aff)}
                  // eslint-disable-next-line no-shadow
                  filterOptions={(options, params) => {
                    const filtered = filter(options, params);

                    const { inputValue } = params;
                    // Suggest the creation of a new value
                    const isExisting = options.some(
                      (option) => inputValue === option,
                    );
                    if (inputValue !== "" && !isExisting) {
                      filtered.push(inputValue);
                    }

                    return filtered;
                  }}
                  getOptionLabel={(option) => {
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
                      // eslint-disable-next-line react/jsx-props-no-spreading
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
        onClose={() => {
          setAddUserRolesDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>
          {`Grant user ${clickedUser?.username} selected roles:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddUserRoles)}>
            {!!errors.roles && (
              <FormValidationError message="Please select at least one role" />
            )}
            <Controller
              name="roles"
              render={({ field: { onChange, value } }) => (
                <Autocomplete
                  multiple
                  onChange={(e, data) => onChange(data)}
                  value={value}
                  options={roles?.filter(
                    (role) => !clickedUser?.roles?.includes(role.id),
                  )}
                  getOptionLabel={(role) => role.id}
                  filterSelectedOptions
                  data-testid="addUserRolesSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.roles}
                      variant="outlined"
                      label="Select Roles"
                      data-testid="addUserRolesTextField"
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
        onClose={() => {
          setEditUserExpirationDateDialogOpen(false);
        }}
        style={{ position: "fixed" }}
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
                    slotProps={{ textField: { variant: "outlined" } }}
                    label="Expiration date (UTC)"
                    showTodayButton={false}
                  />
                </LocalizationProvider>
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
    </Paper>
  );
};

export default UserManagement;

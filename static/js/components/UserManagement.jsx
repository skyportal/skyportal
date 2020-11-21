import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";

import MUIDataTable from "mui-datatables";
import Paper from "@material-ui/core/Paper";
import Chip from "@material-ui/core/Chip";
import CircularProgress from "@material-ui/core/CircularProgress";
import Typography from "@material-ui/core/Typography";
import Box from "@material-ui/core/Box";
import Autocomplete from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import AddCircleIcon from "@material-ui/icons/AddCircle";
import HelpIcon from "@material-ui/icons/Help";
import IconButton from "@material-ui/core/IconButton";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Tooltip from "@material-ui/core/Tooltip";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import Form from "@rjsf/material-ui";

import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "./FormValidationError";
import UserInvitations from "./UserInvitations";
import * as groupsActions from "../ducks/groups";
import * as usersActions from "../ducks/users";
import * as streamsActions from "../ducks/streams";
import * as invitationsActions from "../ducks/invitations";
import * as aclsActions from "../ducks/acls";
import * as rolesActions from "../ducks/roles";

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
  submitFilterButton: {
    marginTop: "1rem",
  },
}));

const dataTableStyles = (theme) =>
  createMuiTheme({
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
  const { invitationsEnabled } = useSelector((state) => state.sysInfo);
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
  const [addUserStreamsDialogOpen, setAddUserStreamsDialogOpen] = useState(
    false
  );
  const [clickedUser, setClickedUser] = useState(null);
  const [dataFetched, setDataFetched] = useState(false);

  const { handleSubmit, errors, reset, control, getValues } = useForm();

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
  }, [dataFetched, dispatch]);

  if (
    !currentUser?.username?.length ||
    !allGroups?.length ||
    !streams?.length ||
    !acls?.length ||
    !roles?.length
  ) {
    return (
      <Box
        display={queryInProgress ? "block" : "none"}
        className={classes.spinnerDiv}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (
    !(
      currentUser.permissions?.includes("System admin") ||
      currentUser.permissions?.includes("Manage users")
    )
  ) {
    return <div>Access denied: Insufficient permissions.</div>;
  }
  allGroups = allGroups.filter((group) => !group.single_user_group);

  const validateGroups = () => {
    const formState = getValues({ nest: true });
    return formState.groups.length >= 1;
  };

  const validateStreams = () => {
    const formState = getValues({ nest: true });
    return formState.streams.length >= 1;
  };

  const validateACLs = () => {
    const formState = getValues({ nest: true });
    return formState.acls.length >= 1;
  };

  const validateRoles = () => {
    const formState = getValues({ nest: true });
    return formState.roles.length >= 1;
  };

  const handleAddUserToGroups = async (formData) => {
    const groupIDs = formData.groups.map((g) => g.id);
    const promises = groupIDs.map((gid) =>
      dispatch(
        groupsActions.addGroupUser({
          username: clickedUser.username,
          admin: false,
          group_id: gid,
        })
      )
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified group(s).")
      );
      reset({ groups: [] });
      setAddUserGroupsDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleAddUserToStreams = async (formData) => {
    const streamIDs = formData.streams.map((g) => g.id);
    const promises = streamIDs.map((sid) =>
      dispatch(
        streamsActions.addStreamUser({
          user_id: clickedUser.id,
          stream_id: sid,
        })
      )
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(
        showNotification("User successfully added to specified stream(s).")
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
      })
    );
    if (result.status === "success") {
      dispatch(showNotification("User successfully granted specified ACL(s)."));
      reset({ acls: [] });
      setAddUserACLsDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleAddUserRoles = async (formData) => {
    const result = await dispatch(
      rolesActions.addUserRoles({
        userID: clickedUser.id,
        roleIds: formData.roles.map((role) => role.id),
      })
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully granted specified role(s).")
      );
      reset({ roles: [] });
      setAddUserRolesDialogOpen(false);
      dispatch(usersActions.fetchUsers(fetchParams));
      setClickedUser(null);
    }
  };

  const handleClickRemoveUserFromGroup = async (username, group_id) => {
    const result = await dispatch(
      groupsActions.deleteGroupUser({ username, group_id })
    );
    if (result.status === "success") {
      dispatch(
        showNotification("User successfully removed from specified group.")
      );
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  const handleClickRemoveUserStreamAccess = async (user_id, stream_id) => {
    const result = await dispatch(
      streamsActions.deleteStreamUser({ user_id, stream_id })
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

  const handleClickDeleteUserRole = async (userID, role) => {
    const result = await dispatch(
      rolesActions.deleteUserRole({ userID, role })
    );
    if (result.status === "success") {
      dispatch(showNotification("User role successfully removed."));
      dispatch(usersActions.fetchUsers(fetchParams));
    }
  };

  // MUI DataTable functions
  const renderName = (dataIndex) => {
    const user = users[dataIndex];
    return (
      <div>
        {`${user.first_name ? user.first_name : ""} ${
          user.last_name ? user.last_name : ""
        }`}
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
        {user.roles.map((role) => (
          <Chip
            label={role}
            onDelete={() => {
              handleClickDeleteUserRole(user.id, role);
            }}
            key={role}
            id={`deleteUserRoleButton_${user.id}_${role}`}
          />
        ))}
      </div>
    );
  };

  const renderRolesHeader = () => (
    <Tooltip
      interactive
      title={
        <>
          <b>Each role is associated with the following ACLs:</b>
          <ul>
            {roles.map((role) => (
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
        {user.acls.map((acl) => (
          <Chip
            label={acl}
            onDelete={() => {
              handleClickDeleteUserACL(user.id, acl);
            }}
            key={acl}
            id={`deleteUserACLButton_${user.id}_${acl}`}
          />
        ))}
      </div>
    );
  };

  const renderACLsHeader = () => (
    <Tooltip
      interactive
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
          .map((group) => (
            <Chip
              label={group.name}
              onDelete={() => {
                handleClickRemoveUserFromGroup(user.username, group.id);
              }}
              key={group.id}
              id={`deleteGroupUserButton_${user.id}_${group.id}`}
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
            id={`deleteStreamUserButton_${user.id}_${stream.id}`}
          />
        ))}
      </div>
    );
  };

  const handleFilterSubmit = async (formData) => {
    setQueryInProgress(true);
    Object.keys(formData).forEach(
      (key) => !formData[key] && delete formData[key]
    );
    setTableFilterList(
      Object.entries(formData).map(([key, value]) => `${key}: ${value}`)
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
        email: {
          type: "string",
          title: "Email",
        },
        role: {
          title: "Role",
          type: "string",
          enum: roles.map((role) => role.id),
        },
        acl: {
          title: "Additional ACL",
          type: "string",
          enum: acls,
        },
        group: {
          title: "Group",
          type: "string",
          enum: allGroups.map((group) => group.name),
        },
        stream: {
          title: "Stream",
          type: "string",
          enum: streams.map((stream) => stream.name),
        },
      },
    };

    return !queryInProgress ? (
      <div>
        <Form
          schema={filterFormSchema}
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
      },
    },
    {
      name: "contact_email",
      label: "Email",
      options: {
        filter: false,
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
      <Paper variant="outlined" className={classes.section}>
        <MuiThemeProvider theme={dataTableStyles(theme)}>
          <MUIDataTable columns={columns} data={users} options={options} />
        </MuiThemeProvider>
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
              id="addUserToGroupsSelect"
              as={
                <Autocomplete
                  multiple
                  options={allGroups.filter(
                    (g) =>
                      !clickedUser?.groups?.map((gr) => gr.id)?.includes(g.id)
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
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateGroups }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                variant="contained"
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
              id="addUserToStreamsSelect"
              as={
                <Autocomplete
                  multiple
                  options={streams.filter(
                    (s) =>
                      !clickedUser?.streams
                        ?.map((strm) => strm.id)
                        ?.includes(s.id)
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
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateStreams }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                variant="contained"
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
              id="addUserACLsSelect"
              as={
                <Autocomplete
                  multiple
                  options={acls.filter(
                    (acl) => !clickedUser?.permissions?.includes(acl)
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
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateACLs }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                variant="contained"
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
              id="addUserRolesSelect"
              as={
                <Autocomplete
                  multiple
                  options={roles?.filter(
                    (role) => !clickedUser?.roles?.includes(role.id)
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
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateRoles }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                variant="contained"
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
    </Paper>
  );
};

export default UserManagement;

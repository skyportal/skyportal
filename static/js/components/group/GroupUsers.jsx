import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
} from "@mui/material/styles";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import Popover from "@mui/material/Popover";
import MUIDataTable from "mui-datatables";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";
import useMediaQuery from "@mui/material/useMediaQuery";
import IconButton from "@mui/material/IconButton";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";

import ManageUserButtons from "./GroupPageManageUserButtons";
import NewGroupUserForm from "../NewGroupUserForm";
import InviteNewGroupUserForm from "../InviteNewGroupUserForm";
import AddUsersFromGroupForm from "../AddUsersFromGroupForm";
import GroupAdmissionRequestsManagement from "./GroupAdmissionRequestsManagement";

const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTableHeadCell: {
        hintIconAlone: {
          marginTop: 0,
        },
        hintIconWithSortIcon: {
          marginTop: 0,
        },
        sortLabelRoot: {
          height: "auto",
          marginBottom: "auto",
        },
      },
    },
  });

const GroupUsers = ({ group, classes, currentUser, theme, isAdmin }) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const [openedPopoverId, setOpenedPopoverId] = React.useState(null);
  const [panelMembersExpanded, setPanelMembersExpanded] =
    React.useState("panel-members");
  const { invitationsEnabled } = useSelector((state) => state.config);

  const handlePopoverOpen = (event, popoverId) => {
    setOpenedPopoverId(popoverId);
    setAnchorEl(event.target);
  };

  const handlePopoverClose = () => {
    setOpenedPopoverId(null);
    setAnchorEl(null);
  };

  const handlePanelMembersChange = (panel) => (event, isExpanded) => {
    setPanelMembersExpanded(isExpanded ? panel : false);
  };

  const openManageUserPopover = Boolean(anchorEl);
  const popoverId = openManageUserPopover ? "manage-user-popover" : undefined;
  // Mobile manage user popover
  const mobile = !useMediaQuery(theme.breakpoints.up("sm"));

  // Set-up members table
  // MUI DataTable functions
  const renderUsername = (dataIndex) => {
    const user = group?.users[dataIndex];
    return (
      <Link to={`/user/${user.id}`} className={classes.filterLink}>
        {user.username}
      </Link>
    );
  };

  const renderAdmin = (dataIndex) => {
    const user = group?.users[dataIndex];
    return (
      user &&
      user.admin && (
        <div style={{ display: "inline-block" }} id={`${user.id}-admin-chip`}>
          <Chip label="Admin" size="small" color="secondary" />
        </div>
      )
    );
  };

  const renderActions = (dataIndex) => {
    const user = group?.users[dataIndex];
    return (
      <div>
        {group &&
          (mobile ? (
            <div>
              <IconButton
                edge="end"
                aria-label="open-manage-user-popover"
                onClick={(e) => handlePopoverOpen(e, user.id)}
                size="large"
              >
                <MoreVertIcon />
              </IconButton>
              <Popover
                id={popoverId}
                open={openedPopoverId === user.id}
                anchorEl={anchorEl}
                onClose={handlePopoverClose}
                anchorOrigin={{
                  vertical: "bottom",
                  horizontal: "center",
                }}
                transformOrigin={{
                  vertical: "top",
                  horizontal: "center",
                }}
              >
                <div className={classes.manageUserPopover}>
                  <ManageUserButtons
                    loadedId={group.id}
                    user={user}
                    isAdmin={isAdmin}
                    group={group}
                    currentUser={currentUser}
                  />
                </div>
              </Popover>
            </div>
          ) : (
            <ManageUserButtons
              loadedId={group.id}
              user={user}
              isAdmin={isAdmin}
              group={group}
              currentUser={currentUser}
            />
          ))}
      </div>
    );
  };

  // Map first and last name into a single name field
  const groupUsers = group?.users?.map((user) => ({
    name: `${user.first_name ? user.first_name : ""} ${
      user.last_name ? user.last_name : ""
    }`,
    ...user,
  }));

  const columns = [
    {
      name: "name",
      label: "Name",
      options: {
        filter: true,
        // Display only if there's at least one user with a first/last name
        display: !!group?.users?.filter(
          (user) => user.first_name || user.last_name,
        )?.length,
      },
    },
    {
      name: "username",
      label: "Username",
      options: {
        filter: true,
        customBodyRenderLite: renderUsername,
      },
    },
    {
      name: "admin",
      label: "Admin",
      options: {
        sort: true,
        customBodyRenderLite: renderAdmin,
        filter: true,
        hint: "An admin is anyone that is a system admin, has group management permissions, and/or is specifically an admin of this group.",
      },
    },
    {
      name: "actions",
      label: "Actions",
      options: {
        sort: false,
        customBodyRenderLite: renderActions,
        filter: false,
        hint: "Note that removing admin status only applies to group-specific admin status. Users who are also system admins and/or have 'Manage groups' permissions will remain admins regardless.",
      },
    },
  ];

  const options = {
    responsive: "standard",
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    rowsPerPage: 25,
    rowsPerPageOptions: [10, 25, 50, 100, 200],
    filter: true,
    jumpToPage: true,
    pagination: true,
    rowHover: false,
  };

  return (
    <Accordion
      expanded={panelMembersExpanded === "panel-members"}
      onChange={handlePanelMembersChange("panel-members")}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        aria-controls="panel-members-content"
        id="panel-members-header"
        className={classes.accordion_summary}
      >
        <Typography className={classes.heading}>Members</Typography>
      </AccordionSummary>
      <AccordionDetails className={classes.accordion_details}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              columns={columns}
              data={group?.users ? groupUsers : []}
              options={options}
            />
          </ThemeProvider>
        </StyledEngineProvider>
        <Divider />
        <div className={classes.paper}>
          {isAdmin(currentUser) && (
            <>
              <br />
              <NewGroupUserForm group_id={group.id} />
              <br />
              {invitationsEnabled && (
                <>
                  <br />
                  <InviteNewGroupUserForm group_id={group.id} />
                </>
              )}
              <br />
              <AddUsersFromGroupForm groupID={group.id} />
              <br />
              <GroupAdmissionRequestsManagement groupID={group.id} />
            </>
          )}
        </div>
      </AccordionDetails>
    </Accordion>
  );
};

GroupUsers.propTypes = {
  group: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    nickname: PropTypes.string,
    users: PropTypes.arrayOf(
      PropTypes.shape({
        username: PropTypes.string,
        id: PropTypes.number,
        first_name: PropTypes.string,
        last_name: PropTypes.string,
      }),
    ),
  }).isRequired,
  classes: PropTypes.shape().isRequired,
  theme: PropTypes.shape().isRequired,
  currentUser: PropTypes.shape({
    username: PropTypes.string,
    id: PropTypes.number,
    first_name: PropTypes.string,
    last_name: PropTypes.string,
    permissions: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  isAdmin: PropTypes.func.isRequired,
};

export default GroupUsers;

import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import Popover from "@mui/material/Popover";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";
import useMediaQuery from "@mui/material/useMediaQuery";
import IconButton from "@mui/material/IconButton";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";

import StyledDataGrid from "../StyledDataGrid";
import ManageUserButtons from "./GroupPageManageUserButtons";
import NewGroupUserForm from "./NewGroupUserForm";
import InviteNewGroupUserForm from "./InviteNewGroupUserForm";
import AddUsersFromGroupForm from "./AddUsersFromGroupForm";
import GroupAdmissionRequestsManagement from "./GroupAdmissionRequestsManagement";

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

  const renderUsername = (params) => {
    const user = params.row;
    return (
      <Link to={`/user/${user.id}`} className={classes.filterLink}>
        {user.username}
      </Link>
    );
  };

  const renderAdmin = (params) => {
    const user = params.row;
    return (
      user &&
      user.admin && (
        <div style={{ display: "inline-block" }} id={`${user.id}-admin-chip`}>
          <Chip label="Admin" size="small" color="secondary" />
        </div>
      )
    );
  };

  const renderActions = (params) => {
    const user = params.row;
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

  const hasNames = !!group?.users?.filter(
    (user) => user.first_name || user.last_name,
  )?.length;

  const columns = [
    { field: "name", headerName: "Name", flex: 1, minWidth: 120 },
    {
      field: "username",
      headerName: "Username",
      flex: 1,
      minWidth: 120,
      renderCell: renderUsername,
    },
    {
      field: "admin",
      headerName: "Admin",
      flex: 1,
      minWidth: 100,
      renderCell: renderAdmin,
      description:
        "An admin is anyone that is a system admin, has group management permissions, and/or is specifically an admin of this group.",
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      renderCell: renderActions,
      description:
        "Note that removing admin status only applies to group-specific admin status. Users who are also system admins and/or have 'Manage groups' permissions will remain admins regardless.",
    },
  ];

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
        <StyledDataGrid
          autoHeight
          columns={columns}
          rows={group?.users ? groupUsers : []}
          getRowId={(row) => row.id}
          initialState={{
            columns: { columnVisibilityModel: { name: hasNames } },
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          pageSizeOptions={[10, 25, 50, 100, 200]}
          showToolbar
        />
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

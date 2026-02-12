import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { StyledEngineProvider } from "@mui/material/styles";
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
import Box from "@mui/material/Box";

import ManageUserButtons from "./GroupPageManageUserButtons";
import AddUserForm from "./AddUserForm";
import InviteNewUserForm from "./InviteNewUserForm";
import AddGroupOfUsersForm from "./AddGroupOfUsersForm";
import GroupAdmissionRequestsManagement from "./GroupAdmissionRequestsManagement";

const GroupUsers = ({ group, currentUser, theme, isAdmin }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [openedPopover, setOpenedPopover] = useState(null);
  const { invitationsEnabled } = useSelector((state) => state.config);
  const mobile = !useMediaQuery(theme.breakpoints.up("sm"));

  const handlePopoverOpen = (event, popoverId) => {
    setOpenedPopover(popoverId);
    setAnchorEl(event.target);
  };

  const handlePopoverClose = () => {
    setOpenedPopover(null);
    setAnchorEl(null);
  };

  const renderUsername = (dataIndex) => {
    const user = group?.users[dataIndex];
    return <Link to={`/user/${user.id}`}>{user.username}</Link>;
  };

  const renderAdmin = (dataIndex) => {
    const user = group?.users[dataIndex];
    return (
      user?.admin && (
        <Chip
          label="Admin"
          size="small"
          id={`${user.id}-admin-chip`}
          color="primary"
        />
      )
    );
  };

  const renderActions = (dataIndex) => {
    if (!group) return null;
    const user = group.users[dataIndex];
    return mobile ? (
      <div>
        <IconButton
          edge="end"
          onClick={(e) => handlePopoverOpen(e, user.id)}
          size="large"
        >
          <MoreVertIcon />
        </IconButton>
        <Popover
          open={openedPopover === user.id}
          anchorEl={anchorEl}
          onClose={handlePopoverClose}
          anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        >
          <ManageUserButtons
            loadedId={group.id}
            user={user}
            isAdmin={isAdmin}
            group={group}
            currentUser={currentUser}
          />
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
    );
  };

  const groupUsers = group?.users?.map((user) => ({
    name: `${user.first_name || ""}${user.first_name && user.last_name && " "}${
      user.last_name || ""
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
    elevation: 0,
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
    <Accordion defaultExpanded>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        aria-controls="panel-members-content"
        id="panel-members-header"
      >
        <Typography variant="h6">Members</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Box display="flex" flexDirection="column" gap={3}>
          <StyledEngineProvider injectFirst>
            <MUIDataTable
              columns={columns}
              data={groupUsers || []}
              options={options}
            />
          </StyledEngineProvider>
          {isAdmin(currentUser) && (
            <>
              <Divider />
              <Typography variant="h6">Adding users to this group</Typography>
              <AddUserForm groupID={group.id} />
              <AddGroupOfUsersForm groupID={group.id} />
              {invitationsEnabled && (
                <>
                  <Divider />
                  <InviteNewUserForm groupID={group.id} />
                </>
              )}
              <Divider />
              <GroupAdmissionRequestsManagement groupID={group.id} />
            </>
          )}
        </Box>
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

import React from "react";
import { Link } from "react-router-dom";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import Popover from "@mui/material/Popover";
import Divider from "@mui/material/Divider";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import useMediaQuery from "@mui/material/useMediaQuery";
import IconButton from "@mui/material/IconButton";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Typography from "@mui/material/Typography";

import StyledDataGrid from "../StyledDataGrid";
import ManageUserButtons from "./GroupPageManageUserButtons";
import AddUserForm from "./AddUserForm";
import InviteNewUserForm from "./InviteNewUserForm";
import AddGroupOfUsersForm from "./AddGroupOfUsersForm";
import GroupAdmissionRequestsManagement from "./GroupAdmissionRequestsManagement";
import { useGetConfigQuery } from "../../ducks/config";

interface GroupUsersProps {
  group: {
    id?: number;
    name?: string;
    nickname?: string | null;
    users?: any[];
  };
  theme: any;
  currentUser: {
    username?: string;
    id?: number;
    first_name?: string;
    last_name?: string;
    permissions?: string[];
  };
  isAdmin: (...a: any[]) => boolean;
}

const GroupUsers = ({
  group,
  currentUser,
  theme,
  isAdmin,
}: GroupUsersProps) => {
  const [anchorEl, setAnchorEl] = React.useState<any>(null);
  const [openedPopoverId, setOpenedPopoverId] = React.useState<any>(null);
  const [panelMembersExpanded, setPanelMembersExpanded] =
    React.useState<any>("panel-members");
  const [userFormTab, setUserFormTab] = React.useState(0);
  const { invitationsEnabled } = (useGetConfigQuery().data as any) ?? {};

  const handlePopoverOpen = (event: any, popoverId: any) => {
    setOpenedPopoverId(popoverId);
    setAnchorEl(event.currentTarget);
  };

  const handlePopoverClose = () => {
    setOpenedPopoverId(null);
    setAnchorEl(null);
  };

  const handlePanelMembersChange =
    (panel: string) => (_event: any, isExpanded: boolean) => {
      setPanelMembersExpanded(isExpanded ? panel : false);
    };

  const openManageUserPopover = Boolean(anchorEl);
  const popoverId = openManageUserPopover ? "manage-user-popover" : undefined;
  // Mobile manage user popover
  const mobile = !useMediaQuery(theme.breakpoints.up("sm"));

  const renderUsername = (params: any) => {
    const user = params.row;
    return <Link to={`/user/${user.id}`}>{user.username}</Link>;
  };

  const renderAdmin = (params: any) => {
    const user = params.row;
    if (!user?.admin) return null;
    return (
      <Chip
        id={`${user.id}-admin-chip`}
        label="Admin"
        size="small"
        color="primary"
      />
    );
  };

  const renderActions = (params: any) => {
    const user = params.row;
    const actions = (
      <ManageUserButtons
        loadedId={group.id!}
        user={user as any}
        isAdmin={isAdmin}
        group={group as any}
        currentUser={currentUser as any}
      />
    );

    if (!group || !mobile) return actions;

    return (
      <>
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
          {actions}
        </Popover>
      </>
    );
  };

  // Map first and last name into a single name field
  const groupUsers = group?.users?.map((user: any) => ({
    name: `${user.first_name ? user.first_name : ""} ${
      user.last_name ? user.last_name : ""
    }`,
    ...user,
  }));

  const hasNames = !!group?.users?.filter(
    (user: any) => user.first_name || user.last_name,
  )?.length;

  const columns: any[] = [
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
        data-testid="tour-group-members"
      >
        <Typography variant="h6">Members</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <StyledDataGrid
          autoHeight
          columns={columns}
          rows={group?.users ? groupUsers : []}
          getRowId={(row: any) => row.id}
          getRowHeight={() => "auto"}
          initialState={{
            columns: { columnVisibilityModel: { name: hasNames } },
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          pageSizeOptions={[10, 25, 50, 100, 200]}
          columnBufferPx={3000}
          showToolbar
        />
        {isAdmin(currentUser) && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mt: 2 }}>
            <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
              <Tabs
                value={userFormTab}
                onChange={(_event, value) => setUserFormTab(value)}
              >
                <Tab label="Add a user" />
                <Tab label="Add a group of users" />
                {invitationsEnabled && <Tab label="Invite a new user" />}
              </Tabs>
            </Box>
            {userFormTab === 0 && <AddUserForm group_id={group.id!} />}
            {userFormTab === 1 && <AddGroupOfUsersForm groupID={group.id!} />}
            {invitationsEnabled && userFormTab === 2 && (
              <InviteNewUserForm group_id={group.id!} />
            )}
            <Divider />
            <GroupAdmissionRequestsManagement groupID={group.id!} />
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  );
};

export default GroupUsers;

import React from "react";
import { Link } from "react-router-dom";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import Popover from "@mui/material/Popover";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import useMediaQuery from "@mui/material/useMediaQuery";
import IconButton from "@mui/material/IconButton";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ManageUserButtons from "./GroupPageManageUserButtons";

const MembersToolbar = () => <DataGridToolbar title="Members" />;

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

  const handlePopoverOpen = (event: any, popoverId: any) => {
    setOpenedPopoverId(popoverId);
    setAnchorEl(event.currentTarget);
  };

  const handlePopoverClose = () => {
    setOpenedPopoverId(null);
    setAnchorEl(null);
  };

  const openManageUserPopover = Boolean(anchorEl);
  const popoverId = openManageUserPopover ? "manage-user-popover" : undefined;
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
    <Box
      sx={{
        p: 1.5,
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <StyledDataGrid
        columns={columns}
        rows={group?.users ? groupUsers : []}
        getRowId={(row: any) => row.id}
        getRowHeight={() => "auto"}
        initialState={{
          columns: { columnVisibilityModel: { name: hasNames } },
        }}
        columnBufferPx={3000}
        disableVirtualization
        showToolbar
        slots={{ toolbar: MembersToolbar }}
      />
    </Box>
  );
};

export default GroupUsers;

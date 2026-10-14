import { useState } from "react";
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

const renderUsername = ({ row }: any) => (
  <Link to={`/user/${row.id}`}>{row.username}</Link>
);

const renderAdmin = ({ row }: any) =>
  row.admin && (
    <Chip
      id={`${row.id}-admin-chip`}
      label="Admin"
      size="small"
      color="primary"
    />
  );

interface GroupUsersProps {
  group: any;
  currentUser: any;
  isAdmin: (user: any) => boolean;
}

const GroupUsers = ({ group, currentUser, isAdmin }: GroupUsersProps) => {
  const [menu, setMenu] = useState<{ anchorEl: Element; userId: number }>();
  const mobile = useMediaQuery((theme: any) => theme.breakpoints.down("sm"));

  const renderActions = ({ row }: any) => {
    const actions = (
      <ManageUserButtons
        loadedId={group.id}
        user={row}
        isAdmin={isAdmin}
        group={group}
        currentUser={currentUser}
      />
    );
    if (!mobile) return actions;
    return (
      <>
        <IconButton
          edge="end"
          aria-label="open-manage-user-popover"
          onClick={(e) =>
            setMenu({ anchorEl: e.currentTarget, userId: row.id })
          }
          size="large"
        >
          <MoreVertIcon />
        </IconButton>
        <Popover
          open={menu?.userId === row.id}
          anchorEl={menu?.anchorEl}
          onClose={() => setMenu(undefined)}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          transformOrigin={{ vertical: "top", horizontal: "center" }}
        >
          {actions}
        </Popover>
      </>
    );
  };

  const rows = (group.users ?? []).map((user: any) => ({
    ...user,
    name: [user.first_name, user.last_name].filter(Boolean).join(" "),
  }));

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
        rows={rows}
        getRowHeight={() => "auto"}
        initialState={{
          columns: {
            columnVisibilityModel: {
              name: rows.some((row: any) => row.name),
            },
          },
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

import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { groupApi } from "../../ducks/group";
import { useUpdateGroupUserMutation } from "../../ducks/groups";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ManageUserButtons from "./GroupPageManageUserButtons";

const MembersToolbar = () => <DataGridToolbar title="Members" />;

const renderUsername = ({ row }: any) => (
  <Link to={`/user/${row.id}`}>{row.username}</Link>
);

interface GroupUsersProps {
  group: any;
  currentUser: any;
  isAdmin: (user: any) => boolean;
}

const GroupUsers = ({ group, currentUser, isAdmin }: GroupUsersProps) => {
  const dispatch = useAppDispatch();
  const [updateGroupUser] = useUpdateGroupUserMutation();
  const canManage = isAdmin(currentUser);
  const numAdmins = (group.users ?? []).filter((u: any) => u.admin).length;

  const togglePermission = async (row: any, param: string, field: string) => {
    const { error } = await updateGroupUser({
      groupID: group.id,
      params: { userID: row.id, [param]: !row[field] },
    });
    if (error) return;
    dispatch(showNotification(`Permissions of ${row.username} updated.`));
    dispatch(groupApi.util.invalidateTags([{ type: "Group", id: group.id }]));
  };

  const permissionColumn = (
    field: string,
    param: string,
    headerName: string,
    extra: Record<string, any> = {},
  ) => ({
    field,
    headerName,
    width: 160,
    align: "center",
    headerAlign: "center",
    renderCell: ({ row }: any) => (
      <Checkbox
        size="small"
        checked={Boolean(row[field])}
        disabled={
          !canManage || (field === "admin" && row.admin && numAdmins === 1)
        }
        onChange={() => togglePermission(row, param, field)}
        data-testid={`${param}-${row.username}`}
      />
    ),
    ...extra,
  });

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
    permissionColumn("admin", "admin", "Admin", {
      description:
        "Admin of this group. System admins and users who can manage groups are admins of every group.",
    }),
    permissionColumn("can_save", "canSave", "Can save"),
    permissionColumn(
      "can_share_photometry",
      "canSharePhotometry",
      "Share photometry",
    ),
    {
      field: "actions",
      headerName: "",
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) => (
        <ManageUserButtons
          user={row}
          isAdmin={isAdmin}
          group={group}
          currentUser={currentUser}
        />
      ),
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

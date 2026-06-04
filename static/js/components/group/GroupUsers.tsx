import React from "react";
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

import { useAppSelector } from "../../types/hooks";
import StyledDataGrid from "../StyledDataGrid";
import ManageUserButtons from "./GroupPageManageUserButtons";
import NewGroupUserForm from "./NewGroupUserForm";
import InviteNewGroupUserForm from "./InviteNewGroupUserForm";
import AddUsersFromGroupForm from "./AddUsersFromGroupForm";
import GroupAdmissionRequestsManagement from "./GroupAdmissionRequestsManagement";

interface GroupUsersProps {
  group: {
    id?: number;
    name?: string;
    nickname?: string;
    users?: any[];
  };
  classes: Record<string, any>;
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
  classes,
  currentUser,
  theme,
  isAdmin,
}: GroupUsersProps) => {
  const [anchorEl, setAnchorEl] = React.useState<any>(null);
  const [openedPopoverId, setOpenedPopoverId] = React.useState<any>(null);
  const [panelMembersExpanded, setPanelMembersExpanded] =
    React.useState<any>("panel-members");
  const { invitationsEnabled } = useAppSelector(
    (state) => state["config"],
  ) as any;

  const handlePopoverOpen = (event: any, popoverId: any) => {
    setOpenedPopoverId(popoverId);
    setAnchorEl(event.target);
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
    return (
      <Link to={`/user/${user.id}`} className={classes["filterLink"]}>
        {user.username}
      </Link>
    );
  };

  const renderAdmin = (params: any) => {
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

  const renderActions = (params: any) => {
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
                <div className={classes["manageUserPopover"]}>
                  <ManageUserButtons
                    loadedId={group.id!}
                    user={user as any}
                    isAdmin={isAdmin}
                    group={group as any}
                    currentUser={currentUser as any}
                  />
                </div>
              </Popover>
            </div>
          ) : (
            <ManageUserButtons
              loadedId={group.id!}
              user={user as any}
              isAdmin={isAdmin}
              group={group as any}
              currentUser={currentUser as any}
            />
          ))}
      </div>
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
        className={classes["accordion_summary"]}
      >
        <Typography className={classes["heading"]}>Members</Typography>
      </AccordionSummary>
      <AccordionDetails className={classes["accordion_details"]}>
        <StyledDataGrid
          autoHeight
          columns={columns}
          rows={group?.users ? groupUsers : []}
          getRowId={(row: any) => row.id}
          // The "actions" cell stacks the admin-toggle buttons above the delete
          // IconButton, which is taller than the default fixed row height. With
          // the grid's default `overflow: hidden` cells that pushes the delete
          // button out of the clickable area. Auto row height lets the full
          // cell content (incl. the delete button) render and stay clickable.
          getRowHeight={() => "auto"}
          initialState={{
            columns: { columnVisibilityModel: { name: hasNames } },
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          pageSizeOptions={[10, 25, 50, 100, 200]}
          // Keep all columns mounted so the rightmost "actions" column (delete
          // buttons) is rendered even when it would otherwise be virtualized
          // out of the horizontal viewport.
          columnBufferPx={3000}
          showToolbar
        />
        <Divider />
        <div className={classes["paper"]}>
          {isAdmin(currentUser) && (
            <>
              <br />
              <NewGroupUserForm group_id={group.id!} />
              <br />
              {invitationsEnabled && (
                <>
                  <br />
                  <InviteNewGroupUserForm group_id={group.id!} />
                </>
              )}
              <br />
              <AddUsersFromGroupForm groupID={group.id!} />
              <br />
              <GroupAdmissionRequestsManagement groupID={group.id!} />
            </>
          )}
        </div>
      </AccordionDetails>
    </Accordion>
  );
};

export default GroupUsers;

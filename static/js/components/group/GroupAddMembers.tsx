import { useState } from "react";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Button from "../Button";
import AddUserForm from "./AddUserForm";
import AddGroupOfUsersForm from "./AddGroupOfUsersForm";
import InviteNewUserForm from "./InviteNewUserForm";
import { useGetConfigQuery } from "../../ducks/config";

const GroupAddMembers = ({ groupID }: { groupID: number }) => {
  const [open, setOpen] = useState(false);
  const [formTab, setFormTab] = useState(0);
  const { invitationsEnabled } = (useGetConfigQuery().data as any) ?? {};

  return (
    <>
      <Tooltip title="Add members">
        <IconButton
          color="primary"
          onClick={() => setOpen(true)}
          data-testid="addMembersButton"
        >
          <PersonAddIcon />
        </IconButton>
      </Tooltip>
      <Dialog
        fullWidth
        maxWidth="md"
        open={open}
        onClose={() => setOpen(false)}
      >
        <DialogTitle>Add members</DialogTitle>
        <Tabs
          value={formTab}
          onChange={(_event, value) => setFormTab(value)}
          sx={{ px: 3, borderBottom: 1, borderColor: "divider" }}
        >
          <Tab label="Add a user" />
          <Tab label="Add a group of users" />
          {invitationsEnabled && <Tab label="Invite a new user" />}
        </Tabs>
        <DialogContent>
          {formTab === 0 && <AddUserForm group_id={groupID} />}
          {formTab === 1 && <AddGroupOfUsersForm groupID={groupID} />}
          {formTab === 2 && <InviteNewUserForm group_id={groupID} />}
        </DialogContent>
        <DialogActions>
          <Button secondary onClick={() => setOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default GroupAddMembers;

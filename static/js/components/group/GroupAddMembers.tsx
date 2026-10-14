import { useState } from "react";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Button from "../Button";
import AddUserForm from "./AddUserForm";
import AddGroupOfUsersForm from "./AddGroupOfUsersForm";
import InviteNewUserForm from "./InviteNewUserForm";
import { useGetConfigQuery } from "../../ducks/config";

export interface AddMembersFormProps {
  groupID: number;
  formId: string;
  onSuccess: () => void;
}

const FORM_ID = "addMembersForm";

const FORMS = [
  { tab: "Add a user", action: "Add user", Form: AddUserForm },
  {
    tab: "Add a group of users",
    action: "Add users",
    Form: AddGroupOfUsersForm,
    testId: "submitAddFromGroupsButton",
  },
  {
    tab: "Invite a new user",
    action: "Invite",
    Form: InviteNewUserForm,
    testId: "inviteNewUserButton",
  },
];

const GroupAddMembers = ({ groupID }: { groupID: number }) => {
  const [open, setOpen] = useState(false);
  const [formTab, setFormTab] = useState(0);
  const { invitationsEnabled } = (useGetConfigQuery().data as any) ?? {};
  const forms = invitationsEnabled ? FORMS : FORMS.slice(0, 2);
  const { action, Form, testId } = forms[formTab]!;
  const close = () => setOpen(false);

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
        maxWidth="sm"
        open={open}
        onClose={close}
        aria-label="Add members"
      >
        <Tabs
          value={formTab}
          onChange={(_event, value) => setFormTab(value)}
          sx={{ px: 1 }}
        >
          {forms.map(({ tab }) => (
            <Tab key={tab} label={tab} />
          ))}
        </Tabs>
        <DialogContent dividers>
          <Form groupID={groupID} formId={FORM_ID} onSuccess={close} />
        </DialogContent>
        <DialogActions>
          <Button secondary onClick={close}>
            Cancel
          </Button>
          <Button primary type="submit" form={FORM_ID} data-testid={testId}>
            {action}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default GroupAddMembers;

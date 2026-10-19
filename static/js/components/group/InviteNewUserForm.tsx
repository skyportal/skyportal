import { useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useInviteUserMutation } from "../../ducks/invitations";
import MemberPermissions, { DEFAULT_PERMISSIONS } from "./MemberPermissions";
import type { AddMembersFormProps } from "./GroupAddMembers";

dayjs.extend(utc);

const InviteNewUserForm = ({
  groupID,
  formId,
  onSuccess,
}: AddMembersFormProps) => {
  const dispatch = useAppDispatch();
  const [inviteUser] = useInviteUserMutation();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("Full user");
  const [expirationDate, setExpirationDate] = useState<Date | null>(null);
  const [permissions, setPermissions] = useState(DEFAULT_PERMISSIONS);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [moreOptions, setMoreOptions] = useState(false);
  const fullUser = role === "Full user";

  const invite = async () => {
    setConfirmOpen(false);
    if (expirationDate && !dayjs.utc(expirationDate).isValid()) {
      dispatch(
        showNotification(
          "Invalid date. Please use MM/DD/YYYY format.",
          "error",
        ),
      );
      return;
    }
    const { error } = await inviteUser({
      userEmail: email,
      groupIDs: [groupID],
      groupAdmin: [fullUser && permissions.admin],
      role,
      streamIDs: null,
      canSave: [permissions.canSave],
      canSharePhotometry: [permissions.canSharePhotometry],
      ...(expirationDate && {
        userExpirationDate: dayjs.utc(expirationDate).toISOString(),
      }),
    } as any);
    if (error) return;
    dispatch(showNotification(`Invitation successfully sent to ${email}`));
    onSuccess();
  };

  return (
    <Box
      component="form"
      id={formId}
      onSubmit={(event) => {
        event.preventDefault();
        setConfirmOpen(true);
      }}
      sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
    >
      <TextField
        label="Email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        data-testid="newUserEmail"
        fullWidth
      />
      <Button
        size="small"
        onClick={() => setMoreOptions(!moreOptions)}
        endIcon={moreOptions ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        aria-expanded={moreOptions}
        sx={{ alignSelf: "flex-start" }}
      >
        More options
      </Button>
      <Collapse in={moreOptions} unmountOnExit>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            select
            label="Role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            fullWidth
          >
            <MenuItem value="Full user">Full user</MenuItem>
            <MenuItem value="View only">View only</MenuItem>
          </TextField>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DatePicker
              label="Account expiration date (UTC)"
              value={expirationDate}
              onChange={setExpirationDate}
              slotProps={{
                textField: {
                  fullWidth: true,
                  helperText:
                    "Optional. The account is deactivated after this date",
                },
              }}
            />
          </LocalizationProvider>
          {fullUser && (
            <MemberPermissions
              value={permissions}
              onChange={setPermissions}
              hide={permissions.canSave ? [] : ["admin"]}
            />
          )}
        </Box>
      </Collapse>
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>Invite new user and add to this group?</DialogTitle>
        <DialogContent>
          An invitation will be sent to {email} with access to this group.
        </DialogContent>
        <DialogActions>
          <Button secondary onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button
            primary
            autoFocus
            onClick={invite}
            data-testid="confirmNewUserButton"
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default InviteNewUserForm;

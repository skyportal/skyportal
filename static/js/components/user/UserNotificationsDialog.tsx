import Alert from "@mui/material/Alert";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import NotificationPreferences from "./preferences/NotificationPreferences";
import { NotificationTarget } from "../notifications/target";

const UserNotificationsDialog = ({
  user,
  onClose,
}: {
  user: any;
  onClose: () => void;
}) => (
  <Dialog open={Boolean(user)} onClose={onClose} fullWidth maxWidth="md">
    <DialogTitle>
      {`Notifications for ${[user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username}`}
    </DialogTitle>
    <DialogContent>
      <Alert severity="info" sx={{ marginBottom: 1.5 }}>
        These are {user?.username}&apos;s own settings, and they see every
        change you make here.
      </Alert>
      {user && (
        <NotificationTarget key={user.id} userId={user.id}>
          <NotificationPreferences />
        </NotificationTarget>
      )}
    </DialogContent>
  </Dialog>
);

export default UserNotificationsDialog;

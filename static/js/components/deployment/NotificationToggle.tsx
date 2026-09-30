import { ReactNode } from "react";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import NotificationSettingsSelect from "../user/preferences/NotificationSettingsSelect";

const NotificationToggle = ({
  type,
  label,
  children,
}: {
  type: string;
  label?: string;
  children: ReactNode;
}) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const active = profile?.preferences["notifications"]?.[type]?.active === true;

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {children}
      </Typography>
      <Stack direction="row" sx={{ alignItems: "center" }}>
        <FormControlLabel
          control={
            <Switch
              checked={active}
              name={type}
              onChange={(event) =>
                updateUserPreferences({
                  notifications: { [type]: { active: event.target.checked } },
                })
              }
            />
          }
          label={label ?? (active ? "Notifications on" : "Notifications off")}
        />
        {active && (
          <NotificationSettingsSelect notificationResourceType={type} />
        )}
      </Stack>
    </>
  );
};

export default NotificationToggle;

import { ReactNode, useState } from "react";

import CallIcon from "@mui/icons-material/CallOutlined";
import EmailIcon from "@mui/icons-material/EmailOutlined";
import TagIcon from "@mui/icons-material/Tag";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import ChannelSetup from "./ChannelSetup";
import { SetupKind, isSetUp } from "./channels";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

const Destination = ({
  icon,
  title,
  value,
  ready,
  actions,
}: {
  icon: ReactNode;
  title: string;
  value: string;
  ready: boolean;
  actions: ReactNode;
}) => (
  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
    <Avatar
      sx={{
        width: 30,
        height: 30,
        "& svg": { fontSize: "1.1rem" },
        bgcolor: ready ? "primary.main" : "action.selected",
        color: ready ? "primary.contrastText" : "text.secondary",
      }}
    >
      {icon}
    </Avatar>
    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      <Typography variant="body2" color="textSecondary" noWrap>
        {value}
      </Typography>
    </Box>
    <Box sx={{ display: "flex", gap: 1, flexShrink: 0 }}>{actions}</Box>
  </Box>
);

const DeliveryChannels = () => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [editing, setEditing] = useState<SetupKind | null>(null);
  if (!profile) return null;

  const slackReady = isSetUp(profile, "slack");
  const edit = (kind: SetupKind, ready: boolean, testId: string) => (
    <Button
      secondary
      size="small"
      onClick={() => setEditing(editing === kind ? null : kind)}
      data-testid={testId}
    >
      {ready ? "Change" : kind === "slack" ? "Connect" : "Add"}
    </Button>
  );

  return (
    <Box
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        padding: "0.75rem",
        display: "flex",
        flexDirection: "column",
        gap: 1,
        backgroundColor: "background.paper",
      }}
    >
      <Box>
        <Typography sx={{ fontWeight: 600 }}>Where notifications go</Typography>
        <Typography variant="body2" color="textSecondary">
          Pick the channels for each kind of notification below.
        </Typography>
      </Box>
      <Destination
        icon={<EmailIcon fontSize="small" />}
        title="Email"
        value={profile.contact_email || "No contact email"}
        ready={isSetUp(profile, "email")}
        actions={edit("email", isSetUp(profile, "email"), "email_edit_button")}
      />
      {editing === "email" && (
        <ChannelSetup
          kind="email"
          onDone={() => setEditing(null)}
          onCancel={() => setEditing(null)}
        />
      )}
      <Destination
        icon={<TagIcon fontSize="small" />}
        title="Slack"
        value={
          slackReady
            ? profile.preferences["slack_integration"].url
            : "Not connected"
        }
        ready={slackReady}
        actions={
          <>
            {edit("slack", slackReady, "slack_connect_button")}
            {slackReady && (
              <Button
                secondary
                size="small"
                data-testid="slack_disconnect_button"
                onClick={() =>
                  updateUserPreferences({
                    slack_integration: { active: false },
                  })
                }
              >
                Disconnect
              </Button>
            )}
          </>
        }
      />
      {editing === "slack" && (
        <ChannelSetup
          kind="slack"
          onDone={() => setEditing(null)}
          onCancel={() => setEditing(null)}
        />
      )}
      <Destination
        icon={<CallIcon fontSize="small" />}
        title="Phone"
        value={profile.contact_phone || "No phone number"}
        ready={isSetUp(profile, "phone")}
        actions={edit("phone", isSetUp(profile, "phone"), "phone_edit_button")}
      />
      {editing === "phone" && (
        <ChannelSetup
          kind="phone"
          onDone={() => setEditing(null)}
          onCancel={() => setEditing(null)}
        />
      )}
    </Box>
  );
};

export default DeliveryChannels;

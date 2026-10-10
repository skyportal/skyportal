import { ReactNode, useState } from "react";

import CheckIcon from "@mui/icons-material/Check";
import NotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import ChannelSchedule from "./ChannelSchedule";
import ToggleRow from "./ToggleRow";
import ChannelSetup from "./ChannelSetup";
import { CHANNELS, ChannelKey, SetupKind, isSetUp } from "./channels";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

const Pill = ({
  icon,
  label,
  on,
  pending,
  hint,
  testId,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  on: boolean;
  pending: boolean;
  hint: string;
  testId: string;
  onClick: () => void;
}) => (
  <Tooltip title={hint}>
    <Box
      role="button"
      tabIndex={0}
      aria-pressed={on}
      data-testid={testId}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick();
        }
      }}
      sx={(theme) => ({
        display: "inline-flex",
        alignItems: "center",
        gap: 0.75,
        padding: "0.375rem 0.875rem",
        borderRadius: 999,
        border: 1,
        borderStyle: pending ? "dashed" : "solid",
        fontSize: "0.875rem",
        fontWeight: 500,
        userSelect: "none",
        cursor: "pointer",
        borderColor: on ? "primary.main" : "divider",
        color: on ? "primary.main" : "text.secondary",
        backgroundColor: on
          ? alpha(theme.palette.primary.main, 0.1)
          : "background.paper",
        transition: "all 120ms",
        "&:hover, &:focus-visible": {
          borderColor: "primary.main",
          outline: "none",
        },
      })}
    >
      {on ? <CheckIcon fontSize="small" /> : icon}
      {label}
    </Box>
  </Tooltip>
);

export const ChannelPills = ({
  type,
  channels = CHANNELS.map((channel) => channel.key),
}: {
  type: string;
  channels?: ChannelKey[];
}) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [setup, setSetup] = useState<{
    kind: SetupKind;
    key: ChannelKey;
  } | null>(null);
  if (!profile) return null;

  const prefs = profile.preferences["notifications"]?.[type] ?? {};
  const update = (values: Record<string, unknown>) =>
    updateUserPreferences({ notifications: { [type]: values } });
  const shown = CHANNELS.filter((channel) => channels.includes(channel.key));
  const scheduled = shown.filter(
    (channel) => channel.scheduled && prefs[channel.key]?.active === true,
  );
  const inApp = prefs.in_app?.active !== false;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 1,
        }}
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ marginRight: 0.5 }}
        >
          Notify me
        </Typography>
        <Pill
          icon={<NotificationsIcon fontSize="small" />}
          label="In the app"
          on={inApp}
          pending={false}
          hint="In the notification bell"
          testId={`channel-${type}-in_app`}
          onClick={() => update({ in_app: { active: !inApp } })}
        />
        {shown.map((channel) => {
          const on = prefs[channel.key]?.active === true;
          const ready = isSetUp(profile, channel.setup);
          return (
            <Pill
              key={channel.key}
              icon={channel.icon}
              label={channel.label}
              on={on}
              pending={!on && !ready}
              hint={
                on
                  ? `Stop sending by ${channel.label}`
                  : ready
                    ? ""
                    : "Not set up yet: click to set it up"
              }
              testId={`channel-${type}-${channel.key}`}
              onClick={() => {
                if (!on && !ready) {
                  setSetup({ kind: channel.setup, key: channel.key });
                } else {
                  setSetup(null);
                  update({ [channel.key]: { active: !on } });
                }
              }}
            />
          );
        })}
      </Box>
      {setup && (
        <ChannelSetup
          key={setup.key}
          kind={setup.kind}
          onCancel={() => setSetup(null)}
          onDone={() => {
            update({ [setup.key]: { active: true } });
            setSetup(null);
          }}
        />
      )}
      {scheduled.map((channel) => (
        <ChannelSchedule key={channel.key} type={type} channel={channel} />
      ))}
    </Box>
  );
};

interface NotificationCardProps {
  type: string;
  title: string;
  text: ReactNode;
  children?: ReactNode;
  channels?: ChannelKey[];
}

const NotificationCard = ({
  type,
  title,
  text,
  children,
  channels,
}: NotificationCardProps) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const active = profile?.preferences["notifications"]?.[type]?.active === true;

  return (
    <Box
      data-testid={`notification-card-${type}`}
      sx={(theme) => ({
        border: 1,
        borderColor: active ? "primary.main" : "divider",
        borderRadius: 2,
        padding: "0.375rem",
        backgroundColor: active
          ? alpha(theme.palette.primary.main, 0.03)
          : "background.paper",
        transition: "border-color 120ms, background-color 120ms",
      })}
    >
      <ToggleRow
        checked={active}
        name={type}
        title={title}
        text={text}
        onToggle={(checked) =>
          updateUserPreferences({
            notifications: { [type]: { active: checked } },
          })
        }
      />
      {active && (
        <Box
          sx={{
            margin: "0.375rem 0.5rem 0.375rem 2.75rem",
            paddingTop: 1.25,
            borderTop: 1,
            borderColor: "divider",
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
          }}
        >
          {children}
          <ChannelPills type={type} {...(channels ? { channels } : {})} />
        </Box>
      )}
    </Box>
  );
};

export default NotificationCard;

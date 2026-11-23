import { ReactNode } from "react";

import CallIcon from "@mui/icons-material/CallOutlined";
import EmailIcon from "@mui/icons-material/EmailOutlined";
import SmsIcon from "@mui/icons-material/SmsOutlined";
import TagIcon from "@mui/icons-material/Tag";
import TelegramIcon from "@mui/icons-material/Telegram";

import type { useGetProfileQuery } from "../../ducks/profile";

export type Profile = NonNullable<
  ReturnType<typeof useGetProfileQuery>["data"]
>;

export type ChannelKey = "email" | "slack" | "telegram" | "sms" | "phone";
export type SetupKind = "email" | "slack" | "telegram" | "phone";

export interface Channel {
  key: ChannelKey;
  label: string;
  icon: ReactNode;
  setup: SetupKind;
  scheduled: boolean;
}

export const CHANNELS: Channel[] = [
  {
    key: "email",
    label: "Email",
    icon: <EmailIcon fontSize="small" />,
    setup: "email",
    scheduled: false,
  },
  {
    key: "slack",
    label: "Slack",
    icon: <TagIcon fontSize="small" />,
    setup: "slack",
    scheduled: false,
  },
  {
    key: "telegram",
    label: "Telegram",
    icon: <TelegramIcon fontSize="small" />,
    setup: "telegram",
    scheduled: false,
  },
  {
    key: "sms",
    label: "SMS",
    icon: <SmsIcon fontSize="small" />,
    setup: "phone",
    scheduled: true,
  },
  {
    key: "phone",
    label: "Phone call",
    icon: <CallIcon fontSize="small" />,
    setup: "phone",
    scheduled: true,
  },
];

export const isSetUp = (profile: Profile, kind: SetupKind) => {
  if (kind === "email") return Boolean(profile.contact_email);
  if (kind === "phone") return Boolean(profile.contact_phone);
  if (kind === "telegram") {
    return (
      profile.preferences["telegram_integration"]?.active === true &&
      Boolean(profile.preferences["telegram_integration"]?.chat_id)
    );
  }
  return (
    profile.preferences["slack_integration"]?.active === true &&
    Boolean(profile.preferences["slack_integration"]?.url)
  );
};

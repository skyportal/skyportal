import { ReactNode } from "react";

import CallIcon from "@mui/icons-material/CallOutlined";
import EmailIcon from "@mui/icons-material/EmailOutlined";
import SmsIcon from "@mui/icons-material/SmsOutlined";
import TagIcon from "@mui/icons-material/Tag";
import WhatsAppIcon from "@mui/icons-material/WhatsApp";

import type { useGetProfileQuery } from "../../ducks/profile";

export type Profile = NonNullable<
  ReturnType<typeof useGetProfileQuery>["data"]
>;

export type ChannelKey = "email" | "slack" | "sms" | "phone" | "whatsapp";
export type SetupKind = "email" | "slack" | "phone";

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
  {
    key: "whatsapp",
    label: "WhatsApp",
    icon: <WhatsAppIcon fontSize="small" />,
    setup: "phone",
    scheduled: true,
  },
];

export const isSetUp = (profile: Profile, kind: SetupKind) =>
  kind === "email"
    ? Boolean(profile.contact_email)
    : kind === "phone"
      ? Boolean(profile.contact_phone)
      : profile.preferences["slack_integration"]?.active === true &&
        Boolean(profile.preferences["slack_integration"]?.url);

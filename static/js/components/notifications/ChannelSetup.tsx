import { FormEvent, ReactNode, useState } from "react";

import CallIcon from "@mui/icons-material/CallOutlined";
import EmailIcon from "@mui/icons-material/EmailOutlined";
import TagIcon from "@mui/icons-material/Tag";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import Button from "../Button";
import type { SetupKind } from "./channels";
import { useGetConfigQuery } from "../../ducks/config";
import {
  useGetProfileQuery,
  useUpdateBasicUserInfoMutation,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

const TEXTS: Record<
  SetupKind,
  { title: string; text: string; label: string; placeholder: string }
> = {
  slack: {
    title: "Connect Slack",
    text: "Ask your site administrator for a webhook URL that posts to your Slack channel.",
    label: "Webhook URL",
    placeholder: "https://hooks.slack.com/services/...",
  },
  email: {
    title: "Add a contact email",
    text: "Notifications are sent to this address. Others see it on your profile only if you make it public.",
    label: "Contact email",
    placeholder: "you@example.org",
  },
  phone: {
    title: "Add a phone number",
    text: "Used for SMS, WhatsApp and phone calls. Include the country code.",
    label: "Phone number",
    placeholder: "+1 555 123 4567",
  },
};

const ICONS: Record<SetupKind, ReactNode> = {
  slack: <TagIcon />,
  email: <EmailIcon />,
  phone: <CallIcon />,
};

interface ChannelSetupProps {
  kind: SetupKind;
  onDone: () => void;
  onCancel?: (() => void) | undefined;
}

const ChannelSetup = ({ kind, onDone, onCancel }: ChannelSetupProps) => {
  const { data: profile } = useGetProfileQuery();
  const preamble = (useGetConfigQuery().data as any)?.slackPreamble ?? "";
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [updateBasicUserInfo] = useUpdateBasicUserInfoMutation();
  const initial =
    kind === "slack"
      ? (profile?.preferences["slack_integration"]?.url ?? "")
      : kind === "email"
        ? (profile?.contact_email ?? "")
        : (profile?.contact_phone ?? "");
  const [value, setValue] = useState<string>(initial);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const { title, text, label, placeholder } = TEXTS[kind];

  const save = async (event: FormEvent) => {
    event.preventDefault();
    const entered = value.trim();
    if (kind === "slack" && !entered.startsWith(preamble)) {
      setError("Must be a Slack URL");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      if (kind === "slack") {
        await updateUserPreferences({
          slack_integration: { active: true, url: entered },
        }).unwrap();
      } else {
        await updateBasicUserInfo({
          formData:
            kind === "email"
              ? { contact_email: entered }
              : { contact_phone: entered },
        }).unwrap();
      }
      onDone();
    } catch (err: any) {
      setError(err?.error ?? err?.data?.message ?? "Could not save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box
      component="form"
      onSubmit={save}
      data-testid={`${kind}-setup`}
      sx={(theme) => ({
        display: "flex",
        gap: 1.5,
        padding: 1.5,
        borderRadius: 2,
        border: 1,
        borderColor: alpha(theme.palette.primary.main, 0.3),
        backgroundColor: alpha(theme.palette.primary.main, 0.04),
      })}
    >
      <Avatar sx={{ width: 36, height: 36, bgcolor: "primary.main" }}>
        {ICONS[kind]}
      </Avatar>
      <Box
        sx={{
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          gap: 1.25,
          minWidth: 0,
        }}
      >
        <Box>
          <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
          <Typography variant="body2" color="textSecondary">
            {text}
          </Typography>
        </Box>
        <TextField
          autoFocus
          size="small"
          name={kind === "slack" ? "url" : kind}
          label={label}
          placeholder={placeholder}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          error={Boolean(error)}
          helperText={error ?? ""}
          slotProps={{ htmlInput: { "data-testid": `${kind}_input` } }}
        />
        <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
          {onCancel && (
            <Button secondary size="small" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button
            primary
            size="small"
            type="submit"
            disabled={!value.trim() || saving}
            data-testid={`${kind}_save_button`}
          >
            {kind === "slack" ? "Connect" : "Save"}
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default ChannelSetup;

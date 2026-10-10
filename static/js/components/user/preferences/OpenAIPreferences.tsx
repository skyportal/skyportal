import React, { useState } from "react";

import Box from "@mui/material/Box";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import CustomizeOpenAIParameters from "./CustomizeOpenAIParameters";

const OpenAIPreferences = () => {
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [apikey, setApikey] = useState(profile.summary?.OpenAI?.apikey);
  const [apikeyerror, setApikeyerror] = useState(false);
  const [baseUrl, setBaseUrl] = useState(profile.summary?.OpenAI?.base_url);
  const [baseUrlError, setBaseUrlError] = useState(false);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setApikey(event.target.value);
  };

  const handleBlur = () => {
    if (apikey) {
      setApikeyerror(false);
      updateUserPreferences({ summary: { OpenAI: { apikey } } });
    } else {
      setApikeyerror(true);
    }
  };

  const handleBaseUrlChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setBaseUrl(event.target.value);
  };

  // Blank is OpenAI itself; anything else must be a URL we can send a key to.
  const handleBaseUrlBlur = () => {
    const trimmed = (baseUrl || "").trim();
    if (trimmed && !trimmed.startsWith("https://")) {
      setBaseUrlError(true);
      return;
    }
    setBaseUrlError(false);
    updateUserPreferences({
      summary: { OpenAI: { base_url: trimmed || null } },
    });
  };

  const prefToggled = (event: React.ChangeEvent<HTMLInputElement>) => {
    const prefs = {
      summary: {
        OpenAI: {
          [event.target.name]: event.target.checked,
        },
      },
    };
    updateUserPreferences(prefs);
  };

  const active = profile.summary?.OpenAI?.active === true;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <FormControlLabel
        control={
          <Switch
            checked={active}
            name="active"
            onChange={prefToggled}
            data-testid="OpenAI_toggle"
          />
        }
        label={<Typography variant="body2">Use my own key</Typography>}
      />
      {active && (
        <>
          <TextField
            name="openai_apikey"
            label="API key"
            fullWidth
            placeholder="API key"
            defaultValue={profile.summary?.OpenAI?.apikey}
            onChange={handleChange}
            onBlur={handleBlur}
            data-testid="OpenAI_apikey"
            helperText={apikeyerror ? "An API key is required" : ""}
            error={apikeyerror}
          />
          <TextField
            name="base_url"
            label="API base URL (optional)"
            fullWidth
            placeholder="https://api.openai.com/v1"
            defaultValue={profile.summary?.OpenAI?.base_url}
            onChange={handleBaseUrlChange}
            onBlur={handleBaseUrlBlur}
            data-testid="OpenAI_base_url"
            helperText={
              baseUrlError
                ? "Must be an https:// URL"
                : "Leave blank for OpenAI. Any service speaking the OpenAI chat-completions protocol works; your key is only ever sent here."
            }
            error={baseUrlError}
          />
          <CustomizeOpenAIParameters />
        </>
      )}
    </Box>
  );
};

export default OpenAIPreferences;

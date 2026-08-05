import React, { useState } from "react";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";

import { makeStyles } from "tss-react/mui";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import CustomizeOpenAIParameters from "./CustomizeOpenAIParameters";

const useStyles = makeStyles()((theme) => ({
  textField: {
    marginLeft: theme.spacing(1),
    marginRight: theme.spacing(1),
    "& p": {
      color: "red",
    },
  },
}));

const OpenAIPreferences = () => {
  const { classes } = useStyles();
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [OpenAIapikey, setOpenAIapikey] = useState(
    profile.summary?.OpenAI?.openai_apikey,
  );
  const [OpenAIapikeyerror, setOpenAIapikeyerror] = useState(false);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setOpenAIapikey(event.target.value);
  };

  const handleBlur = () => {
    if (OpenAIapikey?.startsWith("sk-")) {
      setOpenAIapikeyerror(false);
      const prefs = {
        summary: {
          OpenAI: {
            apikey: OpenAIapikey,
          },
        },
      };
      updateUserPreferences(prefs);
    } else {
      setOpenAIapikeyerror(true);
    }
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

  return (
    <div>
      <FormGroup row>
        <FormControlLabel
          control={
            <Switch
              checked={profile.summary?.OpenAI?.active === true}
              name="active"
              onChange={prefToggled}
              data-testid="OpenAI_toggle"
            />
          }
          label={profile?.summary?.OpenAI?.active ? "Active" : "Inactive"}
        />
        {profile?.summary?.OpenAI?.active && <CustomizeOpenAIParameters />}
      </FormGroup>
      {profile?.summary?.OpenAI?.active && (
        <div>
          <TextField
            name="openai_apikey"
            label="OpenAI API KEY"
            className={classes.textField}
            fullWidth
            placeholder="API KEY"
            defaultValue={profile.summary?.OpenAI?.apikey}
            onChange={handleChange}
            onBlur={handleBlur}
            margin="normal"
            data-testid="OpenAI_apikey"
            helperText={OpenAIapikeyerror ? "Must be a OpenAI API KEY" : ""}
            error={OpenAIapikeyerror}
          />
        </div>
      )}
    </div>
  );
};

export default OpenAIPreferences;

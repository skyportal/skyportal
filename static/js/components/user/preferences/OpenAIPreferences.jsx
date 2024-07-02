import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";

import makeStyles from "@mui/styles/makeStyles";

import * as profileActions from "../../../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";
import CustomizeOpenAIParameters from "./CustomizeOpenAIParameters";

const useStyles = makeStyles((theme) => ({
  textField: {
    marginLeft: theme.spacing(1),
    marginRight: theme.spacing(1),
    "& p": {
      color: "red",
    },
  },
}));

const OpenAIPreferences = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const [OpenAIapikey, setOpenAIapikey] = useState(
    profile.summary?.OpenAI?.openai_apikey,
  );
  const [OpenAIapikeyerror, setOpenAIapikeyerror] = useState(false);

  const handleChange = (event) => {
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
      dispatch(profileActions.updateUserPreferences(prefs));
    } else {
      setOpenAIapikeyerror(true);
    }
  };

  const prefToggled = (event) => {
    const prefs = {
      summary: {
        OpenAI: {
          [event.target.name]: event.target.checked,
        },
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <div>
      <UserPreferencesHeader
        title="OpenAI Summarization Service"
        popupText="With an OpenAI account, you can use your API KEY to generate summaries
          of sources. This is a paid service, and while it does not cost that much
           per source (<$0.01) it can add up. So we ask you to use your own
           OpenAI account for this service. You can get your key here: https://platform.openai.com/account/api-keys"
      />
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

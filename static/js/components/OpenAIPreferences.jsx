import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";

import makeStyles from "@mui/styles/makeStyles";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";

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
  const OpenAI_preamble = useSelector((state) => state.config.OpenAIPreamble);
  const profile = useSelector((state) => state.profile.preferences);
  const dispatch = useDispatch();
  const [OpenAIapikey, setOpenAIapikey] = useState(
    profile.OpenAI_integration?.apikey
  );
  const [OpenAIapikeyerror, setOpenAIapikeyerror] = useState(false);

  const handleChange = (event) => {
    setOpenAIapikey(event.target.value);
  };

  const handleBlur = () => {
    if (OpenAIapikey?.startsWith(OpenAI_preamble)) {
      setOpenAIapikeyerror(false);
      const prefs = {
        OpenAI_integration: {
          openai_apikey: OpenAIapikey,
        },
      };
      dispatch(profileActions.updateUserPreferences(prefs));
    } else {
      setOpenAIapikeyerror(true);
    }
  };

  const prefToggled = (event) => {
    const prefs = {
      OpenAI_integration: {
        [event.target.name]: event.target.checked,
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
              checked={profile.OpenAI_integration?.active === true}
              name="active"
              onChange={prefToggled}
              data-testid="OpenAI_toggle"
            />
          }
          label={profile.OpenAI_integration?.active ? "Active" : "Inactive"}
        />
      </FormGroup>
      {profile.OpenAI_integration?.active && (
        <div>
          <TextField
            name="apikey"
            label="OpenAI API KEY"
            className={classes.textField}
            fullWidth
            placeholder="API KEY"
            defaultValue={profile.OpenAI_integration?.apikey}
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

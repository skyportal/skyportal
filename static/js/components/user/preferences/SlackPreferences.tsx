import { useState } from "react";

import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";

import { makeStyles } from "tss-react/mui";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";
import { useGetConfigQuery } from "../../../ducks/config";

const useStyles = makeStyles()((theme) => ({
  textField: {
    marginLeft: theme.spacing(1),
    marginRight: theme.spacing(1),
    "& p": {
      color: "red",
    },
  },
}));

const SlackPreferences = () => {
  const { classes } = useStyles();
  const slack_preamble = (useGetConfigQuery().data as any)?.slackPreamble;
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [slackurl, setSlackurl] = useState<string | undefined>(
    profile.slack_integration?.url,
  );
  const [slackurlerror, setSlackurlerror] = useState(false);

  const handleChange = (event: any) => {
    setSlackurl(event.target.value);
  };

  const handleBlur = () => {
    if (slackurl?.startsWith(slack_preamble)) {
      setSlackurlerror(false);
      const prefs = {
        slack_integration: {
          url: slackurl,
        },
      };
      updateUserPreferences(prefs);
    } else {
      setSlackurlerror(true);
    }
  };

  const prefToggled = (event: any) => {
    const prefs = {
      slack_integration: {
        [event.target.name]: event.target.checked,
      },
    };

    updateUserPreferences(prefs);
  };

  return (
    <div>
      <UserPreferencesHeader
        title="Slack Integration"
        popupText="You'll need to ask your site administrator to give you a unique
          URL that posts to your Slack channel. Activating the Slack integration
          will allow you to get notifications on Slack, depending on your specific notification preferences."
      />
      <FormGroup row>
        <FormControlLabel
          control={
            <Switch
              checked={profile.slack_integration?.active === true}
              name="active"
              onChange={prefToggled}
              data-testid="slack_toggle"
            />
          }
          label={profile.slack_integration?.active ? "Active" : "Inactive"}
        />
      </FormGroup>
      {profile.slack_integration?.active && (
        <div>
          <TextField
            name="url"
            label="Integration URL"
            className={classes.textField}
            fullWidth
            placeholder="Unique URL connecting to your Slack channel"
            defaultValue={profile.slack_integration?.url}
            onChange={handleChange}
            onBlur={handleBlur}
            margin="normal"
            data-testid="slack_url"
            helperText={slackurlerror ? "Must be a Slack URL" : ""}
            error={slackurlerror}
          />
        </div>
      )}
    </div>
  );
};

export default SlackPreferences;

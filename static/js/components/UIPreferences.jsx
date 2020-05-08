import React from 'react';
import { useSelector, useDispatch } from 'react-redux';

import FormGroup from '@material-ui/core/FormGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import Switch from '@material-ui/core/Switch';

// import { useTheme } from '@material-ui/core/styles';

import * as profileActions from '../ducks/profile';


const UIPreferences = () => {
  const currentTheme = useSelector((state) => state.profile.preferences.theme);
  const dispatch = useDispatch();

  const themeToggled = (event) => {
    const prefs = {
      theme: event.target.checked ? 'dark' : 'light'
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const themeSwitch = (
    <Switch
      value="Dark Mode"
      checked={currentTheme === 'dark'}
      onChange={themeToggled}
    />
  );

  /* To get hold of the current theme:

  const themeCtx = useTheme();
  console.log(themeCtx.palette.type);

  */

  return (
    <div>
      <h2>UI Preferences</h2>

      <FormGroup row>
        <FormControlLabel
          control={themeSwitch}
          label="Dark mode"
        />
      </FormGroup>

    </div>
  );
};

export default UIPreferences;

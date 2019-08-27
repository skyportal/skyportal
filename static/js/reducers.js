import { combineReducers } from 'redux';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

import sourcesReducer from './ducks/fetchSources';
import sourceReducer from './ducks/source';
import plotsReducer from './ducks/fetchSourcePlots';
import groupReducer from './ducks/fetchGroup';
import groupsReducer from './ducks/groups';
import profileReducer from './ducks/userProfile';
import usersReducer from './ducks/user';
import sysInfoReducer from './ducks/sysInfo';
import rotateLogoReducer from './ducks/rotateLogo';


const root = combineReducers({
  source: sourceReducer,
  sources: sourcesReducer,
  group: groupReducer,
  groups: groupsReducer,
  notifications: notificationsReducer,
  profile: profileReducer,
  plots: plotsReducer,
  misc: rotateLogoReducer,
  users: usersReducer,
  sysinfo: sysInfoReducer
});

export default root;

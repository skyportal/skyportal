import { combineReducers } from 'redux';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

import sourcesReducer from './ducks/sources';
import sourceReducer from './ducks/source';
import plotsReducer from './ducks/plots';
import groupReducer from './ducks/group';
import groupsReducer from './ducks/groups';
import profileReducer from './ducks/profile';
import usersReducer from './ducks/users';
import sysInfoReducer from './ducks/sysInfo';
import logoReducer from './ducks/logo';


const root = combineReducers({
  source: sourceReducer,
  sources: sourcesReducer,
  group: groupReducer,
  groups: groupsReducer,
  notifications: notificationsReducer,
  profile: profileReducer,
  plots: plotsReducer,
  logo: logoReducer,
  users: usersReducer,
  sysInfo: sysInfoReducer
});

export default root;

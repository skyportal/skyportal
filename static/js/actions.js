import * as groupsActions from './ducks/groups';
import * as userProfileActions from './ducks/userProfile';
import * as sysinfoActions from './ducks/sysinfo';


export default function hydrate() {
  return (dispatch) => {
    dispatch(sysinfoActions.fetchSystemInfo());
    dispatch(userProfileActions.fetchUserProfile());
    dispatch(groupsActions.fetchGroups());
  };
}

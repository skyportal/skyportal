import * as groupsActions from './ducks/groups';
import * as userProfileActions from './ducks/userProfile';
import * as sysInfoActions from './ducks/sysInfo';


export default function hydrate() {
  return (dispatch) => {
    dispatch(sysInfoActions.fetchSystemInfo());
    dispatch(userProfileActions.fetchUserProfile());
    dispatch(groupsActions.fetchGroups());
  };
}

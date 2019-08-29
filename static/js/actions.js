import * as groupsActions from './ducks/groups';
import * as profileActions from './ducks/profile';
import * as sysInfoActions from './ducks/sysInfo';


export default function hydrate() {
  return (dispatch) => {
    dispatch(sysInfoActions.fetchSystemInfo());
    dispatch(profileActions.fetchUserProfile());
    dispatch(groupsActions.fetchGroups());
  };
}

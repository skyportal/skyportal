import * as groupsActions from './ducks/groups';
import * as profileActions from './ducks/profile';
import * as sysInfoActions from './ducks/sysInfo';
import * as dbInfoActions from './ducks/dbInfo';


export default function hydrate() {
  return (dispatch) => {
    dispatch(sysInfoActions.fetchSystemInfo());
    dispatch(dbInfoActions.fetchDBInfo());
    dispatch(profileActions.fetchUserProfile());
    dispatch(groupsActions.fetchGroups());
  };
}

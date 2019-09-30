import * as groupsActions from './ducks/groups';
import * as profileActions from './ducks/profile';
import * as sysInfoActions from './ducks/sysInfo';
import * as sourceTableStatusActions from './ducks/sourceTableStatus';


export default function hydrate() {
  return (dispatch) => {
    dispatch(sysInfoActions.fetchSystemInfo());
    dispatch(sourceTableStatusActions.fetchSourceTableStatus());
    dispatch(profileActions.fetchUserProfile());
    dispatch(groupsActions.fetchGroups());
  };
}

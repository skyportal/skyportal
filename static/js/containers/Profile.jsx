import { connect } from 'react-redux';

import Profile from '../components/Profile';


const mapStateToProps = (state, ownProps) => (
  {
    profile: state.profile,
    groups: state.groups.latest
  }
);

export default connect(mapStateToProps)(Profile);

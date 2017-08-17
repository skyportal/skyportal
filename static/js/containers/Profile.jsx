import { connect } from 'react-redux';

import Profile from '../components/Profile';

const mapStateToProps = (state, ownProps) => (
  state.profile
);

export default connect(mapStateToProps)(Profile);

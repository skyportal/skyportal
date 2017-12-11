import { connect } from 'react-redux';

import ProfileDropdown from '../components/ProfileDropdown';

const mapStateToProps = (state, ownProps) => (
  { profile: state.profile }
);

export default connect(mapStateToProps)(ProfileDropdown);

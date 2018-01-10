import { connect } from 'react-redux';

import Groups from '../components/Groups';


const mapStateToProps = (state, ownProps) => (
  {
    profile: state.profile
  }
);

export default connect(mapStateToProps)(Groups);

import { connect } from 'react-redux';

import GroupManagement from '../components/GroupManagement';


const mapStateToProps = (state, ownProps) => (
  { groups: state.groups }
);

export default connect(mapStateToProps)(GroupManagement);

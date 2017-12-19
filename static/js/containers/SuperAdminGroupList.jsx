import { connect } from 'react-redux';

import GroupList from '../components/GroupList';

const mapStateToProps = (state, ownProps) => (
  {
    groups: state.groups.all
  }
);

export default connect(mapStateToProps)(GroupList);

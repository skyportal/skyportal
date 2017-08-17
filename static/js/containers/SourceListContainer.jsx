import { connect } from 'react-redux';

import SourceList from '../components/SourceList';

const mapStateToProps = (state, ownProps) => (
  {
    sources: state.sources.latest
  }
);

export default connect(mapStateToProps)(SourceList);

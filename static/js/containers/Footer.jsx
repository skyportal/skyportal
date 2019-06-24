import { connect } from 'react-redux';

import Footer from '../components/Footer';


const mapStateToProps = (state, ownProps) => (
  {
    version: state.sysinfo.version
  }
);

export default connect(mapStateToProps)(Footer);

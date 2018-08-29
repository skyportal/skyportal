import { connect } from 'react-redux';

import * as Action from '../actions';
import NewTokenForm from '../components/NewTokenForm';


const mapDispatchToProps = (dispatch, ownProps) => (
  {
    createToken: formState => dispatch(
      Action.createToken(formState)
    )
  }
);

export default connect(null, mapDispatchToProps)(NewTokenForm);

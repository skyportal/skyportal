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


/*
 *
 * import { connect } from 'react-redux';
 * import { reduxForm } from 'redux-form';
 *
 * import * as Action from '../actions';
 * import NewTokenForm from '../components/NewTokenForm';
 *
 *
 * const mapDispatchToProps = (dispatch, ownProps) => (
 *   {
 *     createToken: formState => dispatch(
 *       Action.createToken(formState)
 *     )
 *   }
 * );
 *
 * const TokenForm = connect(null, mapDispatchToProps)(NewTokenForm);
 *
 * export default reduxForm({
 *   form: 'newTokenForm',
 *   fields: ['acls', 'group_id', 'description']
 * })(TokenForm);
 * // export default connect(null, mapDispatchToProps)(NewTokenForm);*/

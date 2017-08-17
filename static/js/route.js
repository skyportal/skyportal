import React from 'react';
import PropTypes from 'prop-types';
import { Route } from 'react-router';

// See: https://github.com/ReactTraining/react-router/issues/4105#issuecomment-289195202

const renderMergedProps = (component, ...rest) => {
  const finalProps = Object.assign({}, ...rest);
  return (
    React.createElement(component, finalProps)
  );
};

/* Can be used as follows:
 *
 *  <PropsRoute path='/allbooks' component={Books} booksGetter={getAllBooks} />
 *
 * We also add routeProps.match to the props, so that params can be
 * accessed as props.route.
 *
 */
const PropsRoute = ({ component, ...rest }) => (
  <Route
    {...rest}
    render={routeProps => (
      renderMergedProps(component,
                        routeProps,
                        { route: routeProps.match.params },
                        rest)
    )}
  />
);

export default PropsRoute;

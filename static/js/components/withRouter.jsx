import React from "react";

import { useParams } from "react-router-dom";

export default function withRouter(Component) {
  function ComponentWithRouterProp(props) {
    const params = useParams();
    /* eslint-disable react/jsx-props-no-spreading */
    return <Component {...props} route={params} />;
  }

  return ComponentWithRouterProp;
}

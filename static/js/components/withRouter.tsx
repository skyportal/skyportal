import React from "react";

import { useParams } from "react-router-dom";

export default function withRouter<P extends object>(
  Component: React.ComponentType<P>,
) {
  function ComponentWithRouterProp(props: P) {
    const params = useParams();
    return <Component {...props} route={params} />;
  }

  return ComponentWithRouterProp;
}

import React from "react";
import MediaQuery from "react-responsive";
import PropTypes from "prop-types";

const Responsive = ({
  element,
  mobileElement,
  desktopElement,
  mobileStyle,
  desktopStyle,
  mobileProps,
  desktopProps,
  children,
  ...otherProps
}) => {
  /* If the user specifies no element of any sorts,
     we wrap the content in a div */
  if (!(element || desktopElement || mobileElement)) {
    element = "div";
  }

  return (
    <MediaQuery minWidth={768}>
      {(matches) => {
        let renderElement = null;
        let props = {};

        if (matches) {
          renderElement = element || desktopElement;
          props = {
            className: desktopStyle,
            ...desktopProps,
          };
        } else {
          renderElement = element || mobileElement;
          props = {
            className: mobileStyle,
            ...mobileProps,
          };
        }
        if (!renderElement) {
          return null;
        }
        return React.createElement(
          renderElement,
          { ...props, ...otherProps },
          children,
        );
      }}
    </MediaQuery>
  );
};

Responsive.propTypes = {
  element: PropTypes.oneOfType([PropTypes.element, PropTypes.func]),
  mobileElement: PropTypes.oneOfType([PropTypes.element, PropTypes.func]),
  desktopElement: PropTypes.oneOfType([PropTypes.element, PropTypes.func]),

  mobileStyle: PropTypes.string,
  desktopStyle: PropTypes.string,

  // eslint-disable-next-line react/forbid-prop-types
  mobileProps: PropTypes.object,

  // eslint-disable-next-line react/forbid-prop-types
  desktopProps: PropTypes.object,

  children: PropTypes.node,
};

Responsive.defaultProps = {
  element: null,
  mobileElement: null,
  desktopElement: null,
  desktopStyle: "",
  mobileStyle: "",
  mobileProps: {},
  desktopProps: {},
  children: null,
};

export default Responsive;

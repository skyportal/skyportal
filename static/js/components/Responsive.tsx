import React from "react";
import MediaQuery from "react-responsive";

interface ResponsiveProps {
  element?: React.ElementType | null;
  mobileElement?: React.ElementType | null;
  desktopElement?: React.ElementType | null;
  mobileStyle?: string;
  desktopStyle?: string;
  mobileProps?: Record<string, any>;
  desktopProps?: Record<string, any>;
  children?: React.ReactNode;
  [key: string]: any;
}

const Responsive = ({
  element = null,
  mobileElement = null,
  desktopElement = null,
  mobileStyle = "",
  desktopStyle = "",
  mobileProps = {},
  desktopProps = {},
  children = null,
  ...otherProps
}: ResponsiveProps) => {
  /* If the user specifies no element of any sorts,
     we wrap the content in a div */
  if (!(element || desktopElement || mobileElement)) {
    element = "div";
  }

  return (
    <MediaQuery minWidth={768}>
      {(matches: boolean) => {
        let renderElement: React.ElementType | null = null;
        let props: Record<string, any> = {};

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

export default Responsive;

import React, { useEffect, useState, useRef } from "react";

import { useTheme } from "@mui/material/styles";
import TelescopePageDesktop from "./TelescopePageDesktop";
import TelescopePageMobile from "./TelescopePageMobile";

const sidebarWidth = 170;

const TelescopePage = () => {
  const ref = useRef(null);
  const theme = useTheme();
  const initialWidth =
    window.innerWidth - sidebarWidth - 2 * parseInt(theme.spacing(2), 10);
  const [width, setWidth] = useState(initialWidth);

  useEffect(() => {
    const handleResize = () => {
      if (ref.current !== null) {
        setWidth(ref.current.offsetWidth);
      }
    };

    window.addEventListener("resize", handleResize);
  }, [ref]);

  return (
    <div ref={ref}>
      {width <= 1200 ? <TelescopePageMobile /> : <TelescopePageDesktop />}
    </div>
  );
};

export default TelescopePage;

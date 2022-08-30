import React, { useEffect, useState, useRef } from "react";

import { useTheme } from "@mui/material/styles";
import GWDetectorPageDesktop from "./GWDetectorPageDesktop";
import GWDetectorPageMobile from "./GWDetectorPageMobile";

const sidebarWidth = 190;

const GWDetectorPage = () => {
  const ref = useRef(null);
  const theme = useTheme();
  const initialWidth = window.innerWidth - sidebarWidth - 2 * theme.spacing(2);
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
      {width <= 600 ? <GWDetectorPageMobile /> : <GWDetectorPageDesktop />}
    </div>
  );
};

export default GWDetectorPage;

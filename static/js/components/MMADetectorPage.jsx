import React, { useEffect, useState, useRef } from "react";

import { useTheme } from "@mui/material/styles";
import MMADetectorPageDesktop from "./MMADetectorPageDesktop";
import MMADetectorPageMobile from "./MMADetectorPageMobile";

const sidebarWidth = 170;

const MMADetectorPage = () => {
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
      {width <= 600 ? <MMADetectorPageMobile /> : <MMADetectorPageDesktop />}
    </div>
  );
};

export default MMADetectorPage;

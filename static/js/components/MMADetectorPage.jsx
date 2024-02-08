import React from "react";

import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

import MMADetectorPageDesktop from "./MMADetectorPageDesktop";
import MMADetectorPageMobile from "./MMADetectorPageMobile";

const MMADetectorPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));

  return (
    <div>
      {isMobile ? <MMADetectorPageMobile /> : <MMADetectorPageDesktop />}
    </div>
  );
};

export default MMADetectorPage;

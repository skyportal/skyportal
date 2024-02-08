import React from "react";

import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

import EarthquakesPageDesktop from "./EarthquakesPageDesktop";
import EarthquakesPageMobile from "./EarthquakesPageMobile";

const EarthquakesPage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));

  return (
    <div>
      {isMobile ? <EarthquakesPageMobile /> : <EarthquakesPageDesktop />}
    </div>
  );
};

export default EarthquakesPage;

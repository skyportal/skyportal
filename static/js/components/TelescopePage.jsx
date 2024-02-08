import React from "react";

import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import TelescopePageDesktop from "./TelescopePageDesktop";
import TelescopePageMobile from "./TelescopePageMobile";

const TelescopePage = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));

  return (
    <div>{isMobile ? <TelescopePageMobile /> : <TelescopePageDesktop />}</div>
  );
};

export default TelescopePage;

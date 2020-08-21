import React from "react";
import { Link } from "react-router-dom";

import Box from "@material-ui/core/Box";
import Responsive from "./Responsive";
import ProfileDropdown from "./ProfileDropdown";
import Logo from "./Logo";

import styles from "./Main.css";

const HeaderContent = () => (
  <div className={styles.topBannerContent}>
    <div style={{ display: "inline-flex", flexDirection: "row" }}>
      <Logo className={styles.logo} />
      <Link className={styles.title} to="/">
        SkyPortal
      </Link>
      <Box p={2} />
    </div>
    <div style={{ position: "fixed", right: "1rem", top: "1rem" }}>
      <Responsive desktopElement={ProfileDropdown} />
    </div>
  </div>
);

export default HeaderContent;

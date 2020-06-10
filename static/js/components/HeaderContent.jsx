import React from "react";
import { Link } from "react-router-dom";

import Responsive from "./Responsive";
import ProfileDropdown from "./ProfileDropdown";
import Logo from "./Logo";

import styles from "./Main.css";


const HeaderContent = () => (
  <div className={styles.topBannerContent}>
    <div style={{ display: "inline-block", float: "left" }}>
      <Logo className={styles.logo} />
      <Link className={styles.title} to="/">
        SkyPortal ∝
      </Link>
    </div>
    <div style={{ position: "fixed", right: "1em" }}>
      <Responsive desktopElement={ProfileDropdown} />
    </div>
  </div>
);

export default HeaderContent;

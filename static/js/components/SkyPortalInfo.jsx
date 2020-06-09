import React from "react";
import { useSelector } from "react-redux";


const SkyPortalInfo = () => {
  const version = useSelector((state) => state.sysInfo.version);
  return (
    <div style={{ display: "inline-block", paddingLeft: "3em" }}>
      <p style={{ color: "#FFF" }}>
        SkyPortal v
        {version}
        . Please file issues at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
        .
      </p>
    </div>
  );
};

export default SkyPortalInfo;

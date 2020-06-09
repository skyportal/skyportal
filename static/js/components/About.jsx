import React from "react";
import { useSelector } from "react-redux";


const About = () => {
  const version = useSelector((state) => state.sysInfo.version);
  return (
    <div style={{ display: "inline-block", paddingLeft: "3em" }}>
      <p>
        SkyPortal v
        {version}
        . Please file issues at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
        .
      </p>
      <p>
        Project Homepage:
        &nbsp;
        <a href="https://skyportal.io">
          https://skyportal.io
        </a>
      </p>
    </div>
  );
};

export default About;

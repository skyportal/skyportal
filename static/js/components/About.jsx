import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

const About = () => {
  const version = useSelector((state) => state.sysInfo.version);
  return (
    <div style={{ display: "inline-block", paddingLeft: "3em" }}>
      <h2>
        This is SkyPortal&nbsp;
        <code>v{version}</code>.
      </h2>
      <p>
        The project homepage is at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io</a>
      </p>
      <p>
        Documentation lives at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io/docs/</a>
      </p>
      <p>
        You may also interact with SkyPortal through its API. Generate a token
        from your&nbsp;
        <Link to="/profile">profile</Link>
        page, then refer to the&nbsp;
        <a href="https://skyportal.io/docs/api.html">API documentation</a>.
      </p>
      <p>
        Please file issues on our GitHub page at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
      </p>
    </div>
  );
};

export default About;

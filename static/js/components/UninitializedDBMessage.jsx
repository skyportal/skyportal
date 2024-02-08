import React from "react";

const UninitializedDBMessage = () => (
  <div>
    Welcome to SkyPortal. The Sources table is currently empty.
    <br />
    For help with initializing the database, see the&nbsp;
    <a href="https://skyportal.io/docs/setup.html">
      getting started documentation
    </a>
    . Or, click on the <b>+</b> icon in the upper right corner of the table to
    add a source.
  </div>
);

export default UninitializedDBMessage;

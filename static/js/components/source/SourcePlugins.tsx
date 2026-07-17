import React from "react";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import Button from "../Button";

import AlertsSearchButton from "../alert/AlertsSearchButton";

interface SourcePluginsProps {
  source: any;
}

const SourcePlugins = ({ source }: SourcePluginsProps) => {
  const [anchorElArchive, setAnchorElArchive] = React.useState<any>(null);
  const openArchive = Boolean(anchorElArchive);

  return (
    <div>
      <Button
        aria-controls={openArchive ? "basic-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={openArchive ? "true" : undefined}
        onClick={(e: any) => setAnchorElArchive(e.currentTarget)}
        primary
        size="small"
      >
        ALERT ARCHIVES
      </Button>
      <Menu
        transitionDuration={50}
        id="archive-menu"
        anchorEl={anchorElArchive}
        open={openArchive}
        onClose={() => setAnchorElArchive(null)}
        slotProps={{
          list: { "aria-labelledby": "basic-button" },
        }}
      >
        <MenuItem>
          <AlertsSearchButton ra={source.ra} dec={source.dec} survey="ZTF" />
        </MenuItem>
        <MenuItem>
          <AlertsSearchButton ra={source.ra} dec={source.dec} survey="LSST" />
        </MenuItem>
      </Menu>
    </div>
  );
};

export default SourcePlugins;

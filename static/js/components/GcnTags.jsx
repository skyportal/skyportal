import React from "react";
import Chip from "@mui/material/Chip";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  BNS: {
    background: "#468847!important",
  },
  NSBH: {
    background: "#b94a48!important",
  },
  BBH: {
    background: "#333333!important",
  },
  GRB: {
    background: "#f89406!important",
  },
  AMON: {
    background: "#3a87ad!important",
  },
  Terrestrial: {
    background: "#999999!important",
  },
}));

const RenderTags = ({ gcnEvent }) => {
  const styles = useStyles();

  const gcnTags = [];
  gcnEvent.tags?.forEach((tag) => {
    gcnTags.push(tag);
  });
  const gcnTagsUnique = [...new Set(gcnTags)];

  const localizationTags = [];
  gcnEvent.localizations?.forEach((loc) => {
    loc.tags?.forEach((tag) => {
      localizationTags.push(tag.text);
    });
  });
  const localizationTagsUnique = [...new Set(localizationTags)];

  return (
    <div>
      <div>
        {gcnTagsUnique.map((tag) => (
          <Chip className={styles[tag]} size="small" label={tag} key={tag} />
        ))}
      </div>
      <div>
        {localizationTagsUnique.map((tag) => (
          <Chip className={styles[tag]} size="small" label={tag} key={tag} />
        ))}
      </div>
    </div>
  );
};

RenderTags.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string).isRequired,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
  }).isRequired,
};

export default RenderTags;

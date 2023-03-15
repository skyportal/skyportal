import React from "react";
import Chip from "@mui/material/Chip";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  root: {
    margin: "0",
    padding: "0",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
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
  title: {
    margin: 0,
    marginRight: "0.45rem",
    padding: "0",
  },
  chips: {
    padding: "0",
    margin: "0",
    "& > div": {
      marginTop: 0,
      marginBottom: 0,
      marginLeft: "0.05rem",
      marginRight: "0.05rem",
    },
  },
}));

const RenderTags = ({ gcnEvent, show_title = false }) => {
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
    <div className={styles.root}>
      {show_title && <h4 className={styles.title}>Tags:</h4>}
      <div className={styles.chips} name="gcn_triggers-tags">
        {gcnTagsUnique.map((tag) => (
          <Chip className={styles[tag]} size="small" label={tag} key={tag} />
        ))}
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
  show_title: PropTypes.bool,
};

RenderTags.defaultProps = {
  show_title: false,
};
export default RenderTags;

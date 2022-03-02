import React from "react";
import Chip from "@material-ui/core/Chip";
import PropTypes from "prop-types";
import { makeStyles } from "@material-ui/core/styles";

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

  const tags = [];
  gcnEvent.tags?.forEach((tag) => {
    tags.push(tag);
  });
  const tagsUnique = [...new Set(tags)];

  return (
    <>
      {tagsUnique.map((tag) => (
        <Chip className={styles[tag]} size="small" label={tag} key={tag} />
      ))}
    </>
  );
};

RenderTags.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string).isRequired,
  }).isRequired,
};

export default RenderTags;

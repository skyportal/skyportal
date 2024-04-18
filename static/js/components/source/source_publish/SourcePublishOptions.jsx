import React from "react";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";

const useStyles = makeStyles(() => ({
  sourcePublishOptions: {
    marginBottom: "1rem",
    display: "flex",
    flexDirection: "column",
  },
}));

const SourcePublishOptions = ({ options }) => {
  const styles = useStyles();

  return (
    <div className={styles.sourcePublishOptions}>
      {options.map((option) => (
        <FormControlLabel
          key={`source_publish_option_${option.label}`}
          label={`Include ${option.label}?`}
          control={
            <Checkbox
              color="primary"
              title={`Include ${option.label}?`}
              type="checkbox"
              onChange={(event) => option.setCheck(event.target.checked)}
              checked={option.isCheck}
            />
          }
        />
      ))}
    </div>
  );
};

SourcePublishOptions.propTypes = {
  options: PropTypes.arrayOf(
    PropTypes.shape({
      label: PropTypes.string,
      isCheck: PropTypes.bool,
      setCheck: PropTypes.func,
    }),
  ).isRequired,
};

export default SourcePublishOptions;

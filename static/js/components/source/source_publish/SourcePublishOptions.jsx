import React from "react";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { useSelector } from "react-redux";

export const sourcePublishOptionsSchema = (streams, groups, is_elements) => {
  const schema = { type: "object", properties: {} };
  const includeProperty = (text) => ({
    type: "boolean",
    default: true,
    title: text,
  });
  const selectProperty = (text, items) => ({
    type: "array",
    items: {
      type: "integer",
      anyOf: items.map((item) => ({
        enum: [item.id],
        type: "integer",
        title: item.name,
      })),
    },
    uniqueItems: true,
    default: [],
    title: text,
  });
  if (is_elements == null || is_elements.summary) {
    schema.properties.include_summary = includeProperty("Include summary?");
  }
  if (is_elements == null || is_elements.photometry) {
    schema.properties.include_photometry = includeProperty(
      "Include photometry?",
    );
  }
  if (is_elements == null || is_elements.classifications) {
    schema.properties.include_classifications = includeProperty(
      "Include classifications?",
    );
  }
  if (streams?.length > 0 && (is_elements == null || is_elements?.photometry)) {
    schema.properties.streams = selectProperty(
      "Streams to restrict photometry from",
      streams,
    );
  }
  if (
    groups?.length > 0 &&
    (is_elements == null ||
      is_elements?.classifications ||
      is_elements?.photometry)
  ) {
    schema.properties.groups = selectProperty(
      "Groups to restrict data from",
      groups,
    );
  }
  return schema;
};

const useStyles = makeStyles(() => ({
  sourcePublishOptions: {
    marginBottom: "1rem",
    display: "flex",
    flexDirection: "column",
    padding: "0 1rem",
    "& .MuiGrid-item": {
      paddingTop: "0",
    },
  },
}));

const SourcePublishOptions = ({ options, setOptions, isElements }) => {
  const styles = useStyles();
  const streams = useSelector((state) => state.streams);
  const groups = useSelector((state) => state.groups.userAccessible);

  return (
    <div className={styles.sourcePublishOptions}>
      <Form
        formData={options}
        onChange={({ formData }) => setOptions(formData)}
        schema={sourcePublishOptionsSchema(streams, groups, isElements)}
        liveValidate
        validator={validator}
        uiSchema={{
          "ui:submitButtonOptions": { norender: true },
        }}
      />
    </div>
  );
};

SourcePublishOptions.propTypes = {
  options: PropTypes.shape({
    include_summary: PropTypes.bool,
    include_photometry: PropTypes.bool,
    include_classifications: PropTypes.bool,
    groups: PropTypes.arrayOf(PropTypes.number),
    streams: PropTypes.arrayOf(PropTypes.number),
  }).isRequired,
  setOptions: PropTypes.func.isRequired,
  isElements: PropTypes.shape({
    photometry: PropTypes.bool,
    classifications: PropTypes.bool,
  }).isRequired,
};

export default SourcePublishOptions;

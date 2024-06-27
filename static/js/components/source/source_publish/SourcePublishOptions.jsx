import React from "react";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { useSelector } from "react-redux";

export const sourcePublishOptionsSchema = (streams, groups) => {
  const schema = {
    type: "object",
    properties: {
      include_summary: {
        type: "boolean",
        title: "Include summary?",
        default: true,
      },
      include_photometry: {
        type: "boolean",
        title: "Include photometry?",
        default: true,
      },
      include_classifications: {
        type: "boolean",
        title: "Include classifications?",
        default: true,
      },
    },
  };
  if (streams?.length > 0) {
    schema.properties.streams = {
      type: "array",
      items: {
        type: "integer",
        anyOf: streams.map((stream) => ({
          enum: [stream.id],
          type: "integer",
          title: stream.name,
        })),
      },
      uniqueItems: true,
      default: [],
      title: "Streams to restrict photometry from",
    };
  }
  if (groups?.length > 0) {
    schema.properties.groups = {
      type: "array",
      items: {
        type: "integer",
        anyOf: groups.map((group) => ({
          enum: [group.id],
          type: "integer",
          title: group.name,
        })),
      },
      uniqueItems: true,
      default: [],
      title: "Groups to restrict data from",
    };
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
        schema={sourcePublishOptionsSchema(streams, groups)}
        liveValidate
        validator={validator}
        uiSchema={{
          include_photometry: {
            "ui:disabled": !isElements.photometry,
          },
          streams: {
            "ui:disabled": !isElements.photometry,
          },
          include_classifications: {
            "ui:disabled": !isElements.classifications,
          },
          "ui:disabled": !isElements.classifications && !isElements.photometry,
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

import React from "react";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import DialogContent from "@mui/material/DialogContent";
import { useSelector } from "react-redux";

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

const SourcePublishOptions = ({ optionsState, isElements }) => {
  const styles = useStyles();
  const streams = useSelector((state) => state.streams);
  const groups = useSelector((state) => state.groups.userAccessible);
  const VALUE = 0;
  const SETTER = 1;

  const formSchema = {
    type: "object",
    properties: {
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
      streams: {
        type: "array",
        items: {
          type: "integer",
          anyOf: (streams || []).map((stream) => ({
            enum: [stream.id],
            type: "integer",
            title: stream.name,
          })),
        },
        uniqueItems: true,
        default: [],
        title: "Streams to restrict photometry from",
      },
      groups: {
        type: "array",
        items: {
          type: "integer",
          anyOf: (groups || []).map((group) => ({
            enum: [group.id],
            type: "integer",
            title: group.name,
          })),
        },
        uniqueItems: true,
        default: [],
        title: "Groups to restrict data from",
      },
    },
  };

  return (
    <DialogContent className={styles.sourcePublishOptions}>
      <Form
        formData={optionsState[VALUE]}
        onChange={({ formData }) => optionsState[SETTER](formData)}
        schema={formSchema}
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
    </DialogContent>
  );
};

SourcePublishOptions.propTypes = {
  optionsState: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.shape({
        include_photometry: PropTypes.bool,
        include_classifications: PropTypes.bool,
        groups: PropTypes.arrayOf(PropTypes.number),
        streams: PropTypes.arrayOf(PropTypes.number),
      }),
      PropTypes.func,
    ]),
  ).isRequired,
  isElements: PropTypes.shape({
    photometry: PropTypes.bool,
    classifications: PropTypes.bool,
  }).isRequired,
};

export default SourcePublishOptions;

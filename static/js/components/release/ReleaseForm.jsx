import React from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import PropTypes from "prop-types";
import { sourcePublishOptionsSchema } from "../source/source_publish/SourcePublishOptions";
import {
  submitPublicRelease,
  updatePublicRelease,
} from "../../ducks/public_pages/public_release";
import Button from "../Button";

const ReleaseForm = ({ release, setRelease, setOpenReleaseForm }) => {
  const dispatch = useDispatch();
  const streams = useSelector((state) => state.streams);
  const groups = useSelector((state) => state.groups.userAccessible);
  const sourceOptionsSchema = sourcePublishOptionsSchema(streams, groups);
  const releaseSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
      },
      link_name: {
        type: "string",
        title: "Link name to use in the URL",
      },
      description: {
        type: "string",
        title: "Description",
      },
      group_ids: {
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
        title: "Groups that can manage this release",
      },
      auto_publish_enabled: {
        type: "boolean",
        title: "Automatically publish source in this group",
        default: false,
      },
      is_visible: {
        type: "boolean",
        title: "Visible",
        default: true,
      },
      options: {
        title: "Options for the sources in this release",
        ...sourceOptionsSchema,
      },
    },
    required: ["name", "link_name"],
  };

  const submitRelease = () => {
    const action = release.id
      ? updatePublicRelease(release.id, release)
      : submitPublicRelease(release);
    dispatch(action).then((response) => {
      if (response.status === "success") {
        setOpenReleaseForm(false);
        setRelease({});
      }
    });
  };

  return (
    <Form
      formData={release}
      onChange={({ formData }) => setRelease(formData)}
      schema={releaseSchema}
      validator={validator}
      onSubmit={submitRelease}
      uiSchema={{
        link_name: {
          "ui:disabled": !!release.id,
        },
        description: {
          "ui:widget": "textarea",
          "ui:options": {
            rows: 3,
          },
        },
      }}
    >
      <div style={{ display: "flex", justifyContent: "center" }}>
        <Button primary type="submit">
          Submit
        </Button>
      </div>
    </Form>
  );
};

ReleaseForm.propTypes = {
  release: PropTypes.oneOfType([
    PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      link_name: PropTypes.string,
      description: PropTypes.string,
      group_ids: PropTypes.arrayOf(PropTypes.number),
      is_visible: PropTypes.bool,
      options: PropTypes.shape({
        include_summary: PropTypes.bool,
        include_photometry: PropTypes.bool,
        include_classifications: PropTypes.bool,
        groups: PropTypes.arrayOf(PropTypes.number),
        streams: PropTypes.arrayOf(PropTypes.number),
      }),
    }),
    PropTypes.shape({}),
  ]).isRequired,
  setRelease: PropTypes.func.isRequired,
  setOpenReleaseForm: PropTypes.func.isRequired,
};

export default ReleaseForm;

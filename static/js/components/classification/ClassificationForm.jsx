import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import * as Actions from "../../ducks/source";

import CustomProbabilityWidget from "./CustomProbabilityWidget";
import CustomGroupsWidget from "./CustomGroupsWidget";
import { allowedClasses } from "../../utils/helpers";
import CustomClassificationWidget from "./CustomClassificationWidget";

const ClassificationForm = ({ obj_id, taxonomyList }) => {
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);

  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  const [selectedFormData, setSelectedFormData] = useState({});

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    const classification = formData.classification.split(" <> ")[0];
    const data = {
      taxonomy_id: parseInt(formData.taxonomy, 10),
      obj_id,
      classification,
      probability: formData.probability,
      ml: formData.ml || false,
    };
    if (formData.groupIDs) {
      data.group_ids = formData.groupIDs?.map((id) => parseInt(id, 10));
    }
    const result = await dispatch(Actions.addClassification(data));
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Classification saved"));
    }
  };

  const widgets = {
    customClassificationWidget: CustomClassificationWidget,
    customProbabilityWidget: CustomProbabilityWidget,
    customGroupsWidget: CustomGroupsWidget,
  };

  const formSchema = {
    description: "Add Classification",
    type: "object",
    required: ["taxonomy", "classification", "probability"],
    properties: {
      groupIDs: {
        type: "array",
        items: {
          type: "string",
          anyOf: groups?.map((group) => ({
            enum: [group.id.toString()],
            type: "string",
            title: group.name,
          })),
        },
        uniqueItems: true,
      },
      taxonomy: {
        type: "string",
        title: "Taxonomy",
        anyOf: latestTaxonomyList?.map((taxonomy) => ({
          enum: [taxonomy.id.toString()],
          type: "string",
          title: `${taxonomy.name} (${taxonomy.version})`,
        })),
      },
    },
    dependencies: {
      taxonomy: {
        oneOf: [],
      },
    },
  };
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy).map(
      (option) =>
        `${option.class} <> ${
          option.context.length > 0 ? option.context.join(" « ") : ""
        }`,
    );
    formSchema.dependencies.taxonomy.oneOf.push({
      properties: {
        taxonomy: {
          enum: [taxonomy.id.toString()],
        },
        classification: {
          type: "string",
          name: "classification",
          title: "Classification",
          enum: currentClasses,
        },
        probability: {
          type: "number",
          name: "probability",
          title: "Probability",
        },
        ml: {
          type: "boolean",
          name: "ml",
          title: "ML based classification?",
        },
      },
    });
  });
  const uiSchema = {
    groupIDs: { "ui:widget": "customGroupsWidget" },
    classification: { "ui:widget": "customClassificationWidget" },
    probability: { "ui:widget": "customProbabilityWidget" },
  };

  const validate = (formData, errors) => {
    if (formData.classification === "" || !formData.classification) {
      errors.classification.addError("Classification cannot be blank");
    }
    if (formData.probability < 0 || formData.probability > 1) {
      errors.probability.addError(
        "Probability must be between 0 and 1, or blank",
      );
    }
    return errors;
  };

  return (
    <Form
      schema={formSchema}
      validator={validator}
      customValidate={validate}
      uiSchema={uiSchema}
      widgets={widgets}
      onSubmit={handleSubmit}
      disabled={submissionRequestInProcess}
      formData={selectedFormData}
      onChange={({ formData }) => {
        setSelectedFormData(formData);
      }}
    />
  );
};

ClassificationForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  taxonomyList: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      created_at: PropTypes.string,
      isLatest: PropTypes.bool,
      version: PropTypes.string,
    }),
  ).isRequired,
};

export default ClassificationForm;

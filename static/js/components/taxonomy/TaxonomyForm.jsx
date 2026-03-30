import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { submitTaxonomy, modifyTaxonomy } from "../../ducks/taxonomies";
import GroupShareSelect from "../group/GroupShareSelect";

const TaxonomyForm = ({ onClose, taxonomyId = null }) => {
  const dispatch = useDispatch();
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const taxonomyToEdit = taxonomyList.find(
    (taxonomy) => taxonomy.id === taxonomyId,
  );

  const handleSubmit = async ({ formData }) => {
    const dataToSubmit = {
      ...formData,
      group_ids: selectedGroupIds,
    };
    if (formData.hierarchy_file) {
      const parsed = dataUriToBuffer(formData.hierarchy_file);
      dataToSubmit.hierarchy_file = new TextDecoder().decode(parsed.buffer);
    }
    const result = await dispatch(
      taxonomyId
        ? modifyTaxonomy(taxonomyId, dataToSubmit)
        : submitTaxonomy(dataToSubmit),
    );
    if (result.status === "success") {
      dispatch(showNotification("Taxonomy saved"));
      if (typeof onClose === "function") {
        onClose();
      }
    }
  };

  function validate(formData, errors) {
    const nameExists = taxonomyList.some(
      (taxonomy) =>
        taxonomy.name === formData.name && taxonomy.id !== taxonomyId,
    );
    if (nameExists) {
      errors.name.addError("Taxonomy name matches another, please change.");
    }
    return errors;
  }

  const taxonomyFormSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Name",
        description:
          "Short string to make this taxonomy memorable to end users.",
        default: taxonomyToEdit ? taxonomyToEdit.name : undefined,
      },
      version: {
        type: "string",
        title: "Version",
        description: "Semantic version of this taxonomy",
        default: taxonomyToEdit ? taxonomyToEdit.version : undefined,
      },
      provenance: {
        type: "string",
        title: "Provenance",
        description:
          "Identifier (e.g., URL or git hash) that uniquely ties this taxonomy back to an origin or place of record.",
        default: taxonomyToEdit ? taxonomyToEdit.provenance : undefined,
      },
      ...(taxonomyId === null && {
        hierarchy_file: {
          type: "string",
          format: "data-url",
          title: "Taxonomy file",
          description: "Taxonomy file",
        },
        isLatest: {
          type: "boolean",
          title:
            "Consider this the latest version of the taxonomy with this name?",
        },
      }),
    },
    required: ["name", "version", "provenance"],
  };

  return (
    <>
      <Form
        schema={taxonomyFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        customValidate={validate}
      />
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
    </>
  );
};

TaxonomyForm.propTypes = {
  onClose: PropTypes.func,
  taxonomyId: PropTypes.number,
};

export default TaxonomyForm;

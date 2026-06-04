import { useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { fetchTaxonomies, submitTaxonomy } from "../../ducks/taxonomies";

import GroupShareSelect from "../group/GroupShareSelect";

interface NewTaxonomyProps {
  onClose?: (() => void) | null;
}

const NewTaxonomy = ({ onClose = null }: NewTaxonomyProps) => {
  const { taxonomyList } = useAppSelector((state) => state["taxonomies"]);
  const dispatch = useAppDispatch();

  const groups = useAppSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  const handleSubmit = async ({ formData }: { formData: any }) => {
    formData.group_ids = selectedGroupIds;
    const parsed = dataUriToBuffer(formData.hierarchy_file);
    formData.hierarchy_file = new TextDecoder().decode(parsed.buffer);
    dispatch(submitTaxonomy(formData)).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification("Taxonomy saved"));
        dispatch(fetchTaxonomies());
        if (typeof onClose === "function") {
          onClose();
        }
      }
    });
  };

  function validate(formData: any, errors: any) {
    taxonomyList.forEach((taxonomy: any) => {
      if (formData.name === taxonomy.name) {
        errors.name.addError("Taxonomy name matches another, please change.");
      }
    });
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
      },
      version: {
        type: "string",
        title: "Version",
        description: "Semantic version of this taxonomy",
      },
      provenance: {
        type: "string",
        title: "Provenance",
        description:
          "Identifier (e.g., URL or git hash) that uniquely ties this taxonomy back to an origin or place of record.",
      },
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
    },
    required: ["name", "version", "provenance"],
  };

  return (
    <div>
      <Form
        schema={taxonomyFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
        customValidate={validate as any}
        liveValidate
      />
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
    </div>
  );
};

export default NewTaxonomy;

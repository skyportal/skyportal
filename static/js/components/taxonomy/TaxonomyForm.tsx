import { useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import { useGetGroupsQuery } from "../../ducks/groups";
import {
  useGetTaxonomiesQuery,
  useSubmitTaxonomyMutation,
  useModifyTaxonomyMutation,
} from "../../ducks/taxonomies";
import GroupShareSelect from "../group/GroupShareSelect";

interface TaxonomyFormProps {
  onClose?: () => void;
  taxonomyId?: number | null;
}

const TaxonomyForm = ({ onClose, taxonomyId = null }: TaxonomyFormProps) => {
  const dispatch = useAppDispatch();
  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [submitTaxonomy] = useSubmitTaxonomyMutation();
  const [modifyTaxonomy] = useModifyTaxonomyMutation();
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  const taxonomyToEdit = taxonomyList.find(
    (taxonomy: any) => taxonomy.id === taxonomyId,
  );

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const dataToSubmit: any = {
      ...formData,
      group_ids: selectedGroupIds,
    };
    if (formData.hierarchy_file) {
      const parsed = dataUriToBuffer(formData.hierarchy_file);
      dataToSubmit.hierarchy_file = new TextDecoder().decode(parsed.buffer);
    }
    try {
      if (taxonomyId) {
        await modifyTaxonomy({ id: taxonomyId, params: dataToSubmit }).unwrap();
      } else {
        await submitTaxonomy(dataToSubmit).unwrap();
      }
      dispatch(showNotification("Taxonomy saved"));
      onClose?.();
    } catch {
      // error notification handled by the API base query
    }
  };

  function validate(formData: any, errors: any) {
    const nameExists = taxonomyList.some(
      (taxonomy: any) =>
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
        schema={taxonomyFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
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

export default TaxonomyForm;

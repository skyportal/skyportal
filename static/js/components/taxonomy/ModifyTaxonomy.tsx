import { useGetGroupsQuery } from "../../ducks/groups";
import { useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { makeStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import {
  useGetTaxonomiesQuery,
  useModifyTaxonomyMutation,
} from "../../ducks/taxonomies";

import GroupShareSelect from "../group/GroupShareSelect";

const useStyles = makeStyles()(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  taxonomySelect: {
    width: "100%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

interface ModifyTaxonomyProps {
  taxonomy_id: number;
  onClose?: (() => void) | null;
}

const ModifyTaxonomy = ({
  taxonomy_id,
  onClose = null,
}: ModifyTaxonomyProps) => {
  const { classes } = useStyles();

  const { data: taxonomyList } = useGetTaxonomiesQuery();
  const [modifyTaxonomy] = useModifyTaxonomyMutation();
  const dispatch = useAppDispatch();

  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  const handleSubmit = async ({ formData }: { formData: any }) => {
    if (selectedGroupIds.length > 0) {
      formData.group_ids = selectedGroupIds;
    }

    try {
      await modifyTaxonomy({ id: taxonomy_id, params: formData }).unwrap();
      dispatch(showNotification("Taxonomy saved"));
      if (typeof onClose === "function") {
        onClose();
      }
    } catch {
      // error notification handled by the base query
    }
  };

  const taxonomyLookUp: Record<number, any> = {};

  taxonomyList?.forEach((tax: any) => {
    taxonomyLookUp[tax.id] = tax;
  });

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
    },
  };

  return (
    <div className={classes.container}>
      <Form
        schema={taxonomyFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
      />
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
    </div>
  );
};

export default ModifyTaxonomy;

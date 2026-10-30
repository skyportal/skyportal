import { useState } from "react";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useUploadSpatialCatalogsMutation } from "../../ducks/spatialCatalogs";
import { useGetGroupsQuery } from "../../ducks/groups";
import GroupShareSelect from "../group/GroupShareSelect";

const NewSpatialCatalog = () => {
  const dispatch = useAppDispatch();
  const [uploadSpatialCatalogs] = useUploadSpatialCatalogsMutation();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([]);

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const parsed = dataUriToBuffer(formData.file);
    const ascii = new TextDecoder().decode(parsed.buffer);
    const payload = {
      catalogData: ascii,
      catalogName: formData.catalogName,
      group_ids: selectedGroupIds,
    };
    try {
      await uploadSpatialCatalogs(payload).unwrap();
      dispatch(
        showNotification("Saving spatial catalog... please be patient."),
      );
    } catch {
      // error notification is dispatched by the base query
    }
  };

  const spatialCatalogFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Spatial catalog file",
        description: "Spatial catalog file",
      },
      catalogName: {
        type: "string",
        title: "Spatial catalog name",
        description: "Spatial catalog name",
      },
    },
    required: ["file", "catalogName"],
  };

  return (
    <>
      <GroupShareSelect
        groupList={groups}
        setGroupIDs={setSelectedGroupIds}
        groupIDs={selectedGroupIds}
      />
      <Form
        schema={spatialCatalogFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
      />
    </>
  );
};

export default NewSpatialCatalog;

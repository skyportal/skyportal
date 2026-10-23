import { useState } from "react";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import { useUploadGalaxiesMutation } from "../../ducks/galaxies";
import { useGetGroupsQuery } from "../../ducks/groups";
import GroupShareSelect from "../group/GroupShareSelect";

interface NewGalaxyProps {
  handleClose?: (() => void) | null;
}

const NewGalaxy = ({ handleClose = null }: NewGalaxyProps) => {
  const dispatch = useAppDispatch();
  const [uploadGalaxies] = useUploadGalaxiesMutation();
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
      await uploadGalaxies(payload).unwrap();
      if (handleClose) {
        handleClose();
      }
      dispatch(showNotification("Galaxy saved"));
      // The upload invalidates the Galaxies tag, which refetches the active
      // galaxy queries automatically.
    } catch {
      // error notification handled by the baseQuery
    }
  };

  const galaxyFormSchema = {
    type: "object",
    properties: {
      file: {
        type: "string",
        format: "data-url",
        title: "Galaxy catalog file",
        description: "Galaxy file",
      },
      catalogName: {
        type: "string",
        title: "Galaxy catalog name",
        description: "Galaxy catalog name",
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
        schema={galaxyFormSchema as any}
        validator={validator}
        onSubmit={handleSubmit as any}
      />
    </>
  );
};

export default NewGalaxy;

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { dataUriToBuffer } from "data-uri-to-buffer";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import {
  fetchSpatialCatalogs,
  uploadSpatialCatalogs,
} from "../../ducks/spatialCatalogs";

const NewSpatialCatalog = () => {
  const dispatch = useAppDispatch();

  const handleSubmit = async ({ formData }: { formData: any }) => {
    const parsed = dataUriToBuffer(formData.file);
    const ascii = new TextDecoder().decode(parsed.buffer);
    const payload = {
      catalogData: ascii,
      catalogName: formData.catalogName,
    };
    const result: any = await dispatch(uploadSpatialCatalogs(payload));
    if (result.status === "success") {
      dispatch(
        showNotification("Saving spatial catalog... please be patient."),
      );
      dispatch(fetchSpatialCatalogs());
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
    <Form
      schema={spatialCatalogFormSchema as any}
      validator={validator}
      onSubmit={handleSubmit as any}
    />
  );
};

export default NewSpatialCatalog;

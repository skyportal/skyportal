import { useGetGroupsQuery } from "../../ducks/groups";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { sourcePublishOptionsSchema } from "../source/source_publish/SourcePublishOptions";
import {
  useSubmitPublicReleaseMutation,
  useUpdatePublicReleaseMutation,
} from "../../ducks/public_pages/public_release";
import Button from "../Button";
import { useGetStreamsQuery } from "../../ducks/streams";

interface ReleaseFormProps {
  release: any;
  setRelease: (...args: any[]) => void;
  setOpenReleaseForm: (...args: any[]) => void;
}

const ReleaseForm = ({
  release,
  setRelease,
  setOpenReleaseForm,
}: ReleaseFormProps) => {
  const [submitPublicRelease] = useSubmitPublicReleaseMutation();
  const [updatePublicRelease] = useUpdatePublicReleaseMutation();
  const { data: streams = [] } = useGetStreamsQuery();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const sourceOptionsSchema = sourcePublishOptionsSchema(
    streams as any,
    groups as any,
    undefined,
  );
  const releaseSchema: any = {
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
          enum: groups.map((group: any) => group.id),
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

  const submitRelease = async () => {
    try {
      if (release.id) {
        await updatePublicRelease({
          releaseId: release.id,
          payload: release,
        }).unwrap();
      } else {
        await submitPublicRelease(release).unwrap();
      }
      setOpenReleaseForm(false);
      setRelease({});
    } catch {
      // error notification is handled by the base query
    }
  };

  return (
    <Form
      formData={release}
      onChange={
        (({ formData }: { formData: any }) => setRelease(formData)) as any
      }
      schema={releaseSchema as any}
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
        group_ids: {
          "ui:enumNames": groups.map((group: any) => group.name),
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

export default ReleaseForm;

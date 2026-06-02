import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import { sourcePublishOptionsSchema } from "../source/source_publish/SourcePublishOptions";
import {
  submitPublicRelease,
  updatePublicRelease,
} from "../../ducks/public_pages/public_release";
import Button from "../Button";

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
  const dispatch = useAppDispatch();
  const streams = useAppSelector((state) => state.streams);
  const groups = useAppSelector((state) => state.groups.userAccessible);
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

  const submitRelease = () => {
    const action = release.id
      ? updatePublicRelease(release.id, release)
      : submitPublicRelease(release);
    dispatch(action).then((response: any) => {
      if (response.status === "success") {
        setOpenReleaseForm(false);
        setRelease({});
      }
    });
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

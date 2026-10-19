import { GcnEvent } from "../../types";
import { usePostGcnTagMutation } from "../../ducks/gcnTags";
import AddGcnEventValue from "./AddGcnEventValue";

interface AddGcnTagProps {
  gcnEvent: GcnEvent;
}

const AddGcnTag = ({ gcnEvent }: AddGcnTagProps) => {
  const [postGcnTag] = usePostGcnTagMutation();

  return (
    <AddGcnEventValue
      noun="Tag"
      existing={gcnEvent?.tags}
      onSave={(text) =>
        postGcnTag({ dateobs: gcnEvent.dateobs, text }).unwrap()
      }
    />
  );
};

export default AddGcnTag;

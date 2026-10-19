import { usePostGcnAliasMutation } from "../../ducks/gcnEvent";
import AddGcnEventValue from "./AddGcnEventValue";

interface AddGcnAliasProps {
  gcnEvent: {
    dateobs?: string;
    aliases: string[];
  };
}

const AddGcnAlias = ({ gcnEvent }: AddGcnAliasProps) => {
  const [postGcnAlias] = usePostGcnAliasMutation();

  return (
    <AddGcnEventValue
      noun="Alias"
      existing={gcnEvent?.aliases}
      onSave={(alias) =>
        postGcnAlias({
          dateobs: gcnEvent.dateobs as string,
          params: { alias },
        }).unwrap()
      }
    />
  );
};

export default AddGcnAlias;

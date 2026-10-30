import { useGetProfileQuery, useIsReadOnly } from "../../ducks/profile";
import AddIcon from "@mui/icons-material/Add";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";
import {
  useAddGcnEventUserMutation,
  useDeleteGcnEventUserMutation,
} from "../../ducks/gcnEvents";
import { userLabel } from "../../utils/format";
import RemovableChip from "../RemovableChip";

interface GcnAdvocatesProps {
  gcnEvent: {
    dateobs?: string;
    event_users: any[];
  };
}

const GcnAdvocates = ({ gcnEvent }: GcnAdvocatesProps) => {
  const dispatch = useAppDispatch();
  const { data: userProfile } = useGetProfileQuery();
  const isReadOnly = useIsReadOnly();
  const [addGcnEventUser] = useAddGcnEventUserMutation();
  const [deleteGcnEventUser] = useDeleteGcnEventUserMutation();

  const addUser = async () => {
    const result = await addGcnEventUser({
      userID: userProfile!.id,
      gcnEventDateobs: gcnEvent.dateobs as string,
    });
    if ("data" in result)
      dispatch(showNotification("GCN Event User successfully added."));
  };

  const deleteUser = async (id: number) => {
    const result = await deleteGcnEventUser({
      userID: id,
      gcnEventDateobs: gcnEvent.dateobs as string,
    });
    if ("data" in result)
      dispatch(showNotification("GCN Event User successfully deleted."));
  };

  return (
    <>
      {gcnEvent.event_users?.map((eventUser) => (
        <RemovableChip
          key={eventUser.user_id}
          size="small"
          label={userLabel(eventUser, true)}
          {...(!isReadOnly && {
            onDelete: () => deleteUser(eventUser.user_id),
          })}
        />
      ))}
      {!isReadOnly && (
        <AddIcon
          fontSize="small"
          sx={{ height: "0.75rem", cursor: "pointer" }}
          onClick={addUser}
        />
      )}
    </>
  );
};

export default GcnAdvocates;

import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetStreamsQuery,
  useAddStreamUserMutation,
} from "../../ducks/streams";
import Button from "../Button";

// Lists public (auto-join) streams the current user is not yet a member of, with
// a button to add themselves.
const JoinableStreamsList = () => {
  const { data: profile } = useGetProfileQuery();
  const { data: streams } = useGetStreamsQuery();
  const [addStreamUser] = useAddStreamUserMutation();

  const memberStreamIDs = new Set(
    (profile?.streams ?? []).map((s: any) => s.id),
  );
  const joinable = (streams ?? []).filter(
    (s: any) => s.auto_join && !memberStreamIDs.has(s.id),
  );

  if (!profile || joinable.length === 0) {
    return null;
  }

  const handleJoin = async (streamID: number) => {
    try {
      await addStreamUser({
        stream_id: streamID,
        user_id: profile.id,
      }).unwrap();
    } catch {
      // error notification handled by the API layer
    }
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6">Public streams you can join</Typography>
      {joinable.map((stream: any) => (
        <Box
          key={stream.id}
          sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}
        >
          <span>{stream.name}</span>
          <Button
            secondary
            size="small"
            onClick={() => handleJoin(stream.id)}
            data-testid={`joinStreamButton${stream.id}`}
          >
            Join
          </Button>
        </Box>
      ))}
    </Paper>
  );
};

export default JoinableStreamsList;

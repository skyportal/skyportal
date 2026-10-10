import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetStreamsQuery,
  useAddStreamUserMutation,
} from "../../ducks/streams";
import Button from "../Button";

const JoinableStreamsList = () => {
  const { data: profile } = useGetProfileQuery();
  const { data: streams } = useGetStreamsQuery();
  const [addStreamUser] = useAddStreamUserMutation();

  if (!profile || !streams) {
    return null;
  }

  const memberStreamIDs = new Set(
    (profile.streams ?? []).map((s: any) => s.id),
  );
  const joinable = streams.filter(
    (s: any) => s.auto_join && !memberStreamIDs.has(s.id),
  );

  if (joinable.length === 0) {
    return (
      <Typography variant="body2" color="textSecondary">
        You are in every public stream.
      </Typography>
    );
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
    <Box
      sx={{
        border: 1,
        borderColor: "divider",
        borderRadius: 2,
        "& > :not(:last-child)": { borderBottom: 1, borderColor: "divider" },
      }}
    >
      {joinable.map((stream: any) => (
        <Box
          key={stream.id}
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 1,
            padding: "0.5rem 0.75rem",
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {stream.name}
          </Typography>
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
    </Box>
  );
};

export default JoinableStreamsList;

import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";

import { useGetProfileQuery } from "../../ducks/profile";
import {
  useGetStreamsQuery,
  useAddStreamUserMutation,
} from "../../ducks/streams";
import Button from "../Button";
import Paper from "../Paper";

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
    <Paper>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Public streams you can join
      </Typography>
      <List disablePadding>
        {joinable.map((stream: any, index: number) => (
          <ListItem
            key={stream.id}
            divider={index < joinable.length - 1}
            sx={{ gap: 1 }}
          >
            <ListItemText primary={stream.name} sx={{ flexGrow: 0 }} />
            <Button
              secondary
              size="small"
              onClick={() => handleJoin(stream.id)}
              data-testid={`joinStreamButton${stream.id}`}
            >
              Join
            </Button>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default JoinableStreamsList;

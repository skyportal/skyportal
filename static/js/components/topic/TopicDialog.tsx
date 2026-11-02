import { useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import ClassificationSelect from "../classification/ClassificationSelect";
import SelectWithChips from "../SelectWithChips";
import { useGetTagOptionsQuery } from "../../ducks/objectTags";
import {
  Topic,
  useCreateTopicMutation,
  useUpdateTopicMutation,
} from "../../ducks/topics";

interface TopicDialogProps {
  topic?: Topic | undefined;
  onClose: () => void;
  onSaved: (id: number) => void;
}

const TopicDialog = ({ topic, onClose, onSaved }: TopicDialogProps) => {
  const { data: tagOptions } = useGetTagOptionsQuery();
  const [createTopic, { isLoading: creating }] = useCreateTopicMutation();
  const [updateTopic, { isLoading: updating }] = useUpdateTopicMutation();
  const [name, setName] = useState(topic?.name ?? "");
  const [description, setDescription] = useState(topic?.description ?? "");
  const [classifications, setClassifications] = useState<string[]>(
    topic?.classifications ?? [],
  );
  const [tags, setTags] = useState<string[]>(
    (topic?.tags ?? []).map((tag) => tag.name),
  );

  const save = async () => {
    const fields = {
      name: name.trim(),
      description: description.trim() || null,
      classifications,
      tag_ids: (tagOptions ?? [])
        .filter((option: any) => tags.includes(option.name))
        .map((option: any) => option.id),
    };
    const result = topic
      ? await updateTopic({ id: topic.id, ...fields })
      : await createTopic(fields);
    if (!result.error) {
      onSaved(topic ? topic.id : (result.data as { id: number }).id);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{topic ? "Edit topic" : "New topic"}</DialogTitle>
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            paddingTop: 1,
          }}
        >
          <TextField
            label="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoFocus
            required
            slotProps={{ htmlInput: { maxLength: 100 } }}
            data-testid="topicNameInput"
          />
          <TextField
            label="Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            multiline
            minRows={2}
            slotProps={{ htmlInput: { maxLength: 2000 } }}
          />
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            <Typography variant="body2" color="textSecondary">
              Sources join when they get one of these, or when someone posts
              them.
            </Typography>
            <ClassificationSelect
              selectedClassifications={classifications}
              setSelectedClassifications={setClassifications}
            />
            <SelectWithChips
              label="Tags"
              id="topic-tags-select"
              initValue={tags}
              onChange={(event: any) => setTags(event.target.value)}
              options={(tagOptions ?? []).map((option: any) => option.name)}
              searchable
            />
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={save}
          disabled={!name.trim() || creating || updating}
          data-testid="saveTopicButton"
        >
          {topic ? "Save" : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TopicDialog;

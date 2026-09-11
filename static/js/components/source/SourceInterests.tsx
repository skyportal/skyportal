import { ChangeEvent, useState } from "react";
import ChatIcon from "@mui/icons-material/Chat";
import LinkIcon from "@mui/icons-material/Link";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import Button from "../Button";
import CollaborationEntry from "./CollaborationEntry";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useDeleteSourceInterestMutation,
  useGetSourceInterestsQuery,
  useSetSourceInterestMutation,
} from "../../ducks/sourceInterests";

const useStyles = makeStyles()((theme) => ({
  title: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.5rem",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    gap: "0.5rem",
    marginTop: "0.5rem",
  },
  divider: {
    margin: `${theme.spacing(2)} 0 ${theme.spacing(1)}`,
  },
  list: {
    "& > * + *": {
      borderTop: `1px solid ${theme.palette.divider}`,
    },
  },
  interest: {
    display: "flex",
    flexDirection: "column",
    gap: "0.125rem",
    paddingBottom: "0.25rem",
  },
  interestTitle: {
    fontWeight: 600,
  },
  interestLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.25rem",
    maxWidth: "100%",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
}));

const EMPTY_FORM = { title: "", description: "", link: "" };

interface SourceInterestsProps {
  sourceID: string;
  onDiscuss: () => void;
}

const SourceInterests = ({ sourceID, onDiscuss }: SourceInterestsProps) => {
  const { classes } = useStyles();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const { data: profile } = useGetProfileQuery();
  const { data: interests = [] } = useGetSourceInterestsQuery(sourceID);
  const [setInterest] = useSetSourceInterestMutation();
  const [deleteInterest] = useDeleteSourceInterestMutation();

  const field = (name: keyof typeof form) => ({
    value: form[name],
    onChange: (event: ChangeEvent<HTMLInputElement>) =>
      setForm({ ...form, [name]: event.target.value }),
  });

  const register = async () => {
    await setInterest({ obj_id: sourceID, ...form });
    setForm(EMPTY_FORM);
  };

  return (
    <>
      <Tooltip
        title={interests.map((interest) => interest.user.username).join(", ")}
      >
        <span>
          <Button
            secondary
            color={interests.length > 0 ? "success" : "grey"}
            size="small"
            onClick={() => setOpen(true)}
            data-testid="interested-button"
          >
            {interests.some((interest) => interest.user.id === profile?.id)
              ? "Interested"
              : "I'm interested"}
            {interests.length > 0 && ` (${interests.length})`}
          </Button>
        </span>
      </Tooltip>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
        data-testid="interests-dialog"
      >
        <DialogTitle className={classes.title}>
          Interest in {sourceID}
          <Tooltip title="Comments and discussions">
            <IconButton
              size="small"
              onClick={() => {
                setOpen(false);
                onDiscuss();
              }}
              data-testid="discuss-interests-button"
            >
              <ChatIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          {interests.length === 0 ? (
            <Typography variant="body2" color="textSecondary">
              Nobody has registered an interest in this source yet.
            </Typography>
          ) : (
            <div className={classes.list}>
              {interests.map((interest) => (
                <CollaborationEntry
                  key={interest.id}
                  user={interest.user}
                  createdAt={interest.created_at}
                  onDelete={
                    interest.user.id === profile?.id
                      ? () =>
                          deleteInterest({
                            obj_id: sourceID,
                            interest_id: interest.id,
                          })
                      : undefined
                  }
                >
                  <div className={classes.interest}>
                    <Typography
                      variant="subtitle2"
                      className={classes.interestTitle}
                    >
                      {interest.title}
                    </Typography>
                    {interest.description && (
                      <Typography variant="body2" color="textSecondary">
                        {interest.description}
                      </Typography>
                    )}
                    {interest.link && (
                      <Link
                        href={interest.link}
                        target="_blank"
                        rel="noreferrer"
                        variant="caption"
                        className={classes.interestLink}
                      >
                        <LinkIcon fontSize="inherit" />
                        {interest.link}
                      </Link>
                    )}
                  </div>
                </CollaborationEntry>
              ))}
            </div>
          )}

          <Divider className={classes.divider} />
          <Typography variant="subtitle1">Register an interest</Typography>
          <div className={classes.form}>
            <TextField
              label="Title"
              size="small"
              fullWidth
              {...field("title")}
            />
            <TextField
              label="Description"
              size="small"
              fullWidth
              multiline
              minRows={2}
              {...field("description")}
            />
            <TextField label="Link" size="small" fullWidth {...field("link")} />
            <Button
              primary
              disabled={!form.title.trim()}
              onClick={register}
              data-testid="save-interest-button"
            >
              Register
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceInterests;

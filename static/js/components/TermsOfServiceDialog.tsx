import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import ReactMarkdown from "react-markdown";

import Button from "./Button";
import {
  TermsOfService,
  useAcceptTermsOfServiceMutation,
} from "../ducks/terms_of_service";

interface TermsOfServiceDialogProps {
  terms: TermsOfService;
}

// Rendered instead of the app, not on top of it: the backend 403s the rest.
const TermsOfServiceDialog = ({ terms }: TermsOfServiceDialogProps) => {
  const [acceptTerms] = useAcceptTermsOfServiceMutation();
  const [submitting, setSubmitting] = useState(false);

  const onAgree = async () => {
    setSubmitting(true);
    try {
      await acceptTerms().unwrap();
    } catch {
      // leave the dialog up, a failed write must not let the user through
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      maxWidth="md"
      fullWidth
      // No `onClose`: MUI routes backdrop click and escape through it.
      aria-labelledby="terms-of-service-title"
    >
      <DialogTitle id="terms-of-service-title">{terms.title}</DialogTitle>
      <DialogContent dividers>
        <ReactMarkdown>{terms.text}</ReactMarkdown>
      </DialogContent>
      <DialogActions>
        <Button secondary href="/logout">
          Decline and sign out
        </Button>
        <Button primary onClick={onAgree} disabled={submitting}>
          I Agree
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TermsOfServiceDialog;

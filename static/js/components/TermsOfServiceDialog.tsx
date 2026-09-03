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

const TermsOfServiceDialog = ({ terms }: TermsOfServiceDialogProps) => {
  const [acceptTerms] = useAcceptTermsOfServiceMutation();
  const [submitting, setSubmitting] = useState(false);

  const onAgree = async () => {
    setSubmitting(true);
    try {
      await acceptTerms().unwrap();
      window.location.reload();
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      maxWidth="md"
      fullWidth
      // no `onClose`: it would let backdrop click and escape dismiss this
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

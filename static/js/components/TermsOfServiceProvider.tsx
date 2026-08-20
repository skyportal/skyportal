import { useState } from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import ReactMarkdown from "react-markdown";

import {
  useAcceptTermsOfServiceMutation,
  useGetTermsOfServiceQuery,
} from "../ducks/terms_of_service";

// App-level provider, mounted once inside the router. When the instance
// configures terms the user has not accepted, it blocks the app behind a modal
// that can only be resolved by agreeing or signing out.
const TermsOfServiceProvider = () => {
  const { data: terms } = useGetTermsOfServiceQuery();
  const [acceptTerms] = useAcceptTermsOfServiceMutation();
  const [submitting, setSubmitting] = useState(false);

  if (!terms?.required) {
    return null;
  }

  const onAgree = async () => {
    setSubmitting(true);
    try {
      await acceptTerms().unwrap();
    } catch {
      // error notification handled by the base query; leave the dialog up so
      // the user is never let through on a failed write
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      maxWidth="md"
      fullWidth
      // Deliberately no `onClose`: MUI routes both a backdrop click and the
      // escape key through it, so omitting it leaves agreeing or signing out
      // as the only ways past this.
      aria-labelledby="terms-of-service-title"
    >
      <DialogTitle id="terms-of-service-title">{terms.title}</DialogTitle>
      <DialogContent dividers data-testid="terms-of-service-text">
        <ReactMarkdown>{terms.text}</ReactMarkdown>
      </DialogContent>
      <DialogActions>
        <Button
          href="/logout"
          color="secondary"
          data-testid="terms-of-service-decline"
        >
          Decline and sign out
        </Button>
        <Button
          variant="contained"
          onClick={onAgree}
          disabled={submitting}
          data-testid="terms-of-service-agree"
        >
          I Agree
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TermsOfServiceProvider;

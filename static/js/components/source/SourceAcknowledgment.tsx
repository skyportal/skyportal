import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import FormatQuoteIcon from "@mui/icons-material/FormatQuote";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import Spinner from "../Spinner";
import { useGetSourceAcknowledgmentQuery } from "../../ducks/source";

const labelFor = {
  filters: (f: any) => (f.broker ? `${f.filter} (${f.broker})` : f.filter),
  facilities: (f: any) => `${f.instrument} / ${f.telescope}`,
  programs: (p: any) =>
    [p.proposal_id, p.pi && `PI: ${p.pi}`].filter(Boolean).join(" — "),
};

const SECTIONS: [keyof typeof labelFor, string][] = [
  ["filters", "Filters"],
  ["facilities", "Facilities"],
  ["programs", "Programs"],
];

const SourceAcknowledgment = ({ obj_id }: { obj_id: string }) => {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  // Both null until the first response, which is what makes that request the
  // unfiltered one. Detected is held in state rather than read back off the
  // response, so computing the request does not depend on its own result.
  const [detected, setDetected] = useState<Record<string, number[]> | null>(
    null,
  );
  const [selected, setSelected] = useState<Record<string, number[]> | null>(
    null,
  );

  const args = useMemo(() => {
    // Exclusions, not selections: an empty array is dropped from a query
    // string, so "cite nothing" has to be the non-empty side.
    const exclude = (section: string) =>
      (detected?.[section] ?? []).filter(
        (id) => !(selected?.[section] ?? []).includes(id),
      );
    return {
      id: obj_id,
      ...(detected &&
        selected && {
          exclude_filter_ids: exclude("filters"),
          exclude_instrument_ids: exclude("facilities"),
          exclude_allocation_ids: exclude("programs"),
        }),
    };
  }, [obj_id, detected, selected]);

  const { data, isFetching } = useGetSourceAcknowledgmentQuery(args, {
    skip: !open,
  });

  const components = data?.components;

  // Seed every detected item as checked, once, when the dialog first loads.
  useEffect(() => {
    if (components && detected === null) {
      const ids = Object.fromEntries(
        SECTIONS.map(([key]) => [
          key,
          (components[key] ?? []).map((item: any) => item.id),
        ]),
      );
      setDetected(ids);
      setSelected(ids);
    }
  }, [components, detected]);

  const toggle = (section: string, id: number) =>
    setSelected((current) => {
      const ids = current?.[section] ?? [];
      return {
        ...(current ?? {}),
        [section]: ids.includes(id)
          ? ids.filter((i) => i !== id)
          : [...ids, id],
      };
    });

  const onCopy = async () => {
    await navigator.clipboard.writeText(data?.text ?? "");
    dispatch(showNotification("Acknowledgment copied to clipboard."));
  };

  const populated = SECTIONS.filter(
    ([key]) => (components?.[key] ?? []).length > 0,
  );

  return (
    <>
      <Tooltip title="How to cite this source">
        <IconButton
          size="small"
          onClick={() => setOpen(true)}
          data-testid="acknowledgmentButton"
        >
          <FormatQuoteIcon />
        </IconButton>
      </Tooltip>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>How to cite {obj_id}</DialogTitle>
        <DialogContent>
          {!data ? (
            <Spinner />
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Paper
                variant="outlined"
                sx={{ p: 1.5, opacity: isFetching ? 0.5 : 1 }}
              >
                <Typography
                  variant="body1"
                  data-testid="acknowledgmentText"
                  sx={{ whiteSpace: "pre-wrap" }}
                >
                  {data.text}
                </Typography>
              </Paper>

              {populated.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  Nothing beyond the instance itself was detected for this
                  source.
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  An object usually passes several filters. Tick only what the
                  paper actually used.
                </Typography>
              )}

              {populated.map(([key, title]) => (
                <Box key={key}>
                  <Typography variant="subtitle2">{title}</Typography>
                  {(components[key] ?? []).map((item: any) => (
                    <Box key={item.id}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            size="small"
                            checked={selected?.[key]?.includes(item.id) ?? true}
                            onChange={() => toggle(key, item.id)}
                            data-testid={`ack-${key}-${item.id}`}
                          />
                        }
                        label={labelFor[key](item)}
                      />
                    </Box>
                  ))}
                </Box>
              ))}

              <Box>
                <Button
                  primary
                  onClick={onCopy}
                  data-testid="copyAcknowledgment"
                >
                  Copy
                </Button>
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceAcknowledgment;

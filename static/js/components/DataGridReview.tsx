import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

const waitFor = async (selector: string) => {
  for (let i = 0; i < 100 && !document.querySelector(selector); i++) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
};

const closeDialog = () => {
  const container = document.querySelector(".MuiDialog-container");
  ["mousedown", "click"].forEach((type) =>
    container?.dispatchEvent(new MouseEvent(type, { bubbles: true })),
  );
};

const apiData = async (url: string) =>
  (await (await fetch(url, { credentials: "include" })).json()).data;

const click = (selector: string) =>
  document
    .querySelector(selector)
    ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

type Go = (path: string) => void;

const sourceDialog = (trigger: string) => async (go: Go) => {
  go(`/source/${(await apiData("/api/sources?numPerPage=1")).sources[0].id}`);
  await waitFor(trigger);
  click(trigger);
};

const STEPS: { title: string; open: (go: Go) => Promise<void> }[] = [
  { title: "Brokers list", open: async (go) => go("/brokers") },
  {
    title: "Filter catalog (Filters tab)",
    open: async (go) => {
      const brokers = await apiData("/api/brokers");
      go(
        `/brokers/${brokers.find((b: any) => b.broker_classname === "BOOMBROKER")?.id}`,
      );
      await waitFor('[role="tab"]');
      [...document.querySelectorAll<HTMLElement>('[role="tab"]')]
        .find((tab) => tab.textContent === "Filters")
        ?.click();
    },
  },
  {
    title: "MMA detector events",
    open: async (go) => {
      go("/mmadetectors");
      await waitFor('[aria-label^="show gcn events for"]');
      click('[aria-label^="show gcn events for"]');
    },
  },
  {
    title: "Moving object obs plan",
    open: async (go) => go("/moving_objects/obsplan"),
  },
  {
    title: "Save history",
    open: sourceDialog('[aria-label="source-save-history"]'),
  },
  {
    title: "Redshift history",
    open: sourceDialog('[data-testid="redshiftHistoryIconButton"]'),
  },
  {
    title: "Candidates history",
    open: sourceDialog('[aria-label="Candidates History"]'),
  },
  {
    title: "Summary history",
    open: sourceDialog('[aria-label="Show history of object summaries"]'),
  },
];

const DataGridReview = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [visible, setVisible] = useState(pathname === "/");
  const [step, setStep] = useState(-1);

  if (!visible) return null;

  const goToStep = async (index: number) => {
    closeDialog();
    setStep(index);
    await STEPS[index]?.open((path) => navigate(path));
  };

  return (
    <Paper
      elevation={8}
      sx={{
        position: "fixed",
        bottom: 16,
        right: 16,
        zIndex: 2100,
        p: 2,
        width: 300,
      }}
    >
      <Typography variant="subtitle2">
        DataGrid review{step >= 0 ? ` (${step + 1}/${STEPS.length})` : ""}
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", my: 1 }}>
        {step >= 0 ? STEPS[step]?.title : "Walk through every migrated table."}
      </Typography>
      <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
        <Button size="small" onClick={() => setVisible(false)}>
          Close
        </Button>
        <Button
          size="small"
          disabled={step <= 0}
          onClick={() => goToStep(step - 1)}
        >
          Back
        </Button>
        <Button
          size="small"
          variant="contained"
          disabled={step === STEPS.length - 1}
          onClick={() => goToStep(step + 1)}
        >
          {step < 0 ? "Start" : "Next"}
        </Button>
      </Stack>
    </Paper>
  );
};

export default DataGridReview;

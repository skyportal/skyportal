import { ReactNode } from "react";

import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";

const smallText = {
  fontSize: "0.8125rem",
  "& .MuiTypography-root, & .MuiFormControlLabel-label, & .MuiInputLabel-root":
    {
      fontSize: "0.8125rem",
    },
  "& .MuiFormControl-root, & .MuiInputBase-root": { maxWidth: "25rem" },
};

export interface PreferencesSection {
  title?: string;
  popupText?: string;
  content: ReactNode;
}

interface PreferencesPanelProps {
  title: string;
  popupText?: string | undefined;
  testId?: string | undefined;
  sections: PreferencesSection[];
  expanded: boolean;
  onToggle: () => void;
}

export const Help = ({ text }: { text: string }) => (
  <Tooltip
    title={text}
    placement="right"
    slotProps={{ tooltip: { sx: { maxWidth: "30rem" } } }}
  >
    <HelpOutlineOutlinedIcon fontSize="inherit" sx={{ ml: 0.5 }} />
  </Tooltip>
);

const PreferencesPanel = ({
  title,
  testId,
  sections,
  expanded,
  onToggle,
}: PreferencesPanelProps) => (
  <Accordion
    disableGutters
    elevation={0}
    sx={{
      "&:not(:last-of-type)": { borderBottom: 1, borderColor: "divider" },
    }}
    expanded={expanded}
    onChange={onToggle}
    data-testid={testId}
    slotProps={{ transition: { unmountOnExit: true } }}
  >
    <AccordionSummary
      expandIcon={<ExpandMoreIcon fontSize="small" />}
      data-testid={`${title.toLowerCase().replace(/\s+/g, "-")}-panel`}
    >
      <Typography variant="subtitle1" sx={{ display: "flex", fontWeight: 600 }}>
        {title}
      </Typography>
    </AccordionSummary>
    <AccordionDetails
      sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 0 }}
    >
      {sections.map((section, index) => (
        <div key={section.title ?? index}>
          {section.title && (
            <Typography
              variant="subtitle2"
              sx={{ display: "flex", fontWeight: 600 }}
            >
              {section.title}
              {section.popupText && <Help text={section.popupText} />}
            </Typography>
          )}
          <Box sx={smallText}>{section.content}</Box>
        </div>
      ))}
    </AccordionDetails>
  </Accordion>
);

export default PreferencesPanel;

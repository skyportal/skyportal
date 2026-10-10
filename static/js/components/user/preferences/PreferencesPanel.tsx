import { ReactNode } from "react";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export interface PreferencesSection {
  title?: string;
  text?: ReactNode;
  content: ReactNode;
}

const PreferencesPanel = ({ sections }: { sections: PreferencesSection[] }) => (
  <Box sx={{ display: "flex", flexDirection: "column" }}>
    {sections.map(({ title, text, content }, index) =>
      title ? (
        <Box
          key={title}
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "16rem minmax(0, 1fr)" },
            gap: { xs: 1.5, md: 4 },
            paddingY: 2.5,
            borderTop: index ? 1 : 0,
            borderColor: "divider",
            "&:first-of-type": { paddingTop: 0.5 },
          }}
        >
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {title}
            </Typography>
            {text && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ marginTop: 0.5 }}
              >
                {text}
              </Typography>
            )}
          </Box>
          <Box sx={{ minWidth: 0, maxWidth: "44rem" }}>{content}</Box>
        </Box>
      ) : (
        <Box
          key={index}
          sx={
            index
              ? { borderTop: 1, borderColor: "divider", paddingTop: 2.5 }
              : undefined
          }
        >
          {content}
        </Box>
      ),
    )}
  </Box>
);

export default PreferencesPanel;

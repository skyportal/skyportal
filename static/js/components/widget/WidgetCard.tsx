import { ReactNode } from "react";

import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { SxProps, Theme } from "@mui/material/styles";

import { useActiveTeam } from "../../ducks/teams";

export const TeamBadge = () => {
  const { activeTeam } = useActiveTeam();
  if (!activeTeam) return null;
  return (
    <Box
      component="span"
      sx={{
        px: 0.75,
        py: 0.125,
        borderRadius: 1,
        fontSize: "0.7rem",
        fontWeight: 600,
        whiteSpace: "nowrap",
        color: "#fff",
        bgcolor: activeTeam.primary_color || "primary.main",
      }}
    >
      {activeTeam.name}
    </Box>
  );
};

export const WidgetEmpty = ({ children }: { children: ReactNode }) => (
  <Box
    sx={{
      height: "100%",
      minHeight: "4rem",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      color: "text.secondary",
      typography: "body2",
      px: 1,
    }}
  >
    {children}
  </Box>
);

interface WidgetCardProps {
  title?: ReactNode;
  heading?: ReactNode;
  actions?: ReactNode;
  teamScoped?: boolean;
  children?: ReactNode;
  testId?: string;
  bodySx?: SxProps<Theme>;
}

const WidgetCard = ({
  title,
  heading,
  actions,
  teamScoped = false,
  children,
  testId,
  bodySx = {},
}: WidgetCardProps) => {
  const floatingHeader = !title && !heading;
  return (
    <Paper
      data-testid={testId}
      elevation={0}
      sx={(theme) => ({
        position: "relative",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        borderRadius: 3,
        border: 1,
        borderColor: "divider",
        bgcolor:
          theme.palette.mode === "light" ? "common.white" : "background.paper",
        boxShadow: "0 1px 2px rgba(16, 24, 40, 0.05)",
        transition: "box-shadow 0.2s ease",
        "&:hover": { boxShadow: "0 8px 24px rgba(16, 24, 40, 0.08)" },
      })}
    >
      <Box
        className="dragHandle"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          minHeight: "2.75rem",
          px: 2,
          pt: 1,
          pb: 0.5,
          cursor: "grab",
          userSelect: "none",
          "&:active": { cursor: "grabbing" },
          ...(floatingHeader && {
            position: "absolute",
            top: 0,
            right: 0,
            zIndex: 1,
          }),
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            minWidth: 0,
            flex: 1,
          }}
        >
          {heading ??
            (title && (
              <Typography
                variant="h6"
                noWrap
                sx={{ fontSize: "1rem", fontWeight: 600, lineHeight: 1.4 }}
              >
                {title}
              </Typography>
            ))}
          {teamScoped && <TeamBadge />}
        </Box>
        {actions && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.25,
              flexShrink: 0,
              mr: -1,
              cursor: "default",
            }}
          >
            {actions}
          </Box>
        )}
      </Box>
      <Box
        sx={[
          { flex: 1, minHeight: 0, overflowY: "auto", px: 2, pb: 2 },
          ...(Array.isArray(bodySx) ? bodySx : [bodySx]),
        ]}
      >
        {children}
      </Box>
    </Paper>
  );
};

export default WidgetCard;

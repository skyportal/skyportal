import { ReactNode } from "react";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";

export const Header = ({
  icon,
  title,
  subtitle,
  onBack,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
  onBack?: (() => void) | undefined;
}) => (
  <Box
    sx={{
      display: "flex",
      alignItems: "center",
      gap: 1.5,
      padding: "0.75rem 1rem",
      borderBottom: 1,
      borderColor: "divider",
    }}
  >
    {onBack && (
      <IconButton size="small" onClick={onBack}>
        <ArrowBackIcon fontSize="small" />
      </IconButton>
    )}
    <Avatar sx={{ width: 40, height: 40, bgcolor: "primary.main" }}>
      {icon}
    </Avatar>
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="h6" noWrap sx={{ lineHeight: 1.3 }}>
        {title}
      </Typography>
      <Typography variant="body2" color="textSecondary" noWrap>
        {subtitle}
      </Typography>
    </Box>
  </Box>
);

export const Body = ({
  children,
  wide = false,
}: {
  children: ReactNode;
  wide?: boolean;
}) => (
  <Box sx={{ flexGrow: 1, minHeight: 0, overflowY: "auto" }}>
    <Box
      sx={{
        maxWidth: wide ? "none" : "40rem",
        margin: "0 auto",
        padding: "1.25rem 1rem",
        display: "flex",
        flexDirection: "column",
        gap: 1,
      }}
    >
      {children}
    </Box>
  </Box>
);

export const Empty = ({ children }: { children: ReactNode }) => (
  <Typography
    variant="body2"
    color="textSecondary"
    sx={{ textAlign: "center", padding: 3 }}
  >
    {children}
  </Typography>
);

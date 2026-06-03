import MuiPaper from "@mui/material/Paper";

interface PaperProps {
  noPadding?: boolean;
  sx?: Record<string, any>;
  [key: string]: any;
}

const Paper = ({ noPadding, sx, ...props }: PaperProps) => {
  return (
    <MuiPaper
      sx={{
        ...(noPadding ? {} : { padding: "1rem" }),
        ...sx,
      }}
      {...props}
    />
  );
};

export default Paper;

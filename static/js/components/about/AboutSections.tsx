import { ReactNode } from "react";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { alpha, Theme } from "@mui/material/styles";
import HomeIcon from "@mui/icons-material/Home";
import DescriptionIcon from "@mui/icons-material/Description";
import CodeIcon from "@mui/icons-material/Code";
import GitHubIcon from "@mui/icons-material/GitHub";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import { useAppDispatch } from "../../types/hooks";

const headingColor = (theme: Theme) =>
  theme.palette.mode === "dark"
    ? theme.palette.text.primary
    : theme.palette.primary.dark;

const surface = (theme: Theme) =>
  theme.palette.mode === "dark"
    ? theme.palette.background.paper
    : theme.palette.common.white;

const host = (url: string) =>
  url.replace(/^https?:\/\//, "").replace(/\/$/, "");

export const SectionTitle = ({ children }: { children: ReactNode }) => (
  <Typography variant="h6" sx={{ fontWeight: 700, color: headingColor }}>
    {children}
  </Typography>
);

export const AboutCard = ({
  title,
  children,
}: {
  title?: ReactNode;
  children: ReactNode;
}) => (
  <Paper
    variant="outlined"
    sx={{ p: { xs: 2, md: 3 }, borderRadius: 2, bgcolor: surface }}
  >
    <Stack spacing={2}>
      {title && <SectionTitle>{title}</SectionTitle>}
      {children}
    </Stack>
  </Paper>
);

export const LinkPills = ({
  homepage,
  docs,
  api,
  repository,
}: {
  homepage: string;
  docs: string;
  api: string;
  repository: string;
}) => {
  const links = [
    { label: host(homepage), url: homepage, icon: <HomeIcon /> },
    { label: "Documentation", url: docs, icon: <DescriptionIcon /> },
    { label: "API", url: api, icon: <CodeIcon /> },
    { label: "GitHub", url: repository, icon: <GitHubIcon /> },
  ];
  return (
    <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1.5 }}>
      {links.map((link, index) => (
        <Chip
          key={link.label}
          component="a"
          href={link.url}
          clickable
          icon={link.icon}
          label={link.label}
          color="primary"
          variant={index === 0 ? "filled" : "outlined"}
          sx={{ fontWeight: 600, px: 0.5 }}
        />
      ))}
    </Stack>
  );
};

export interface Instance {
  name: string;
  url: string;
  description?: string;
}

export const InstanceBlocks = ({ instances }: { instances: Instance[] }) => (
  <Box
    sx={{
      display: "grid",
      gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
      gap: 2,
    }}
  >
    {instances.map((instance) => (
      <Paper
        key={instance.name}
        component="a"
        href={instance.url}
        variant="outlined"
        sx={{
          display: "flex",
          flexDirection: "column",
          minHeight: "12rem",
          overflow: "hidden",
          borderRadius: 2,
          bgcolor: surface,
          textDecoration: "none",
          transition: "box-shadow 0.15s ease, transform 0.15s ease",
          "&:hover": {
            borderColor: "primary.main",
            boxShadow: (theme) =>
              `0 6px 16px ${alpha(theme.palette.primary.dark, 0.15)}`,
            transform: "translateY(-2px)",
          },
          "&:hover .instanceName": { bgcolor: "primary.main" },
        }}
      >
        <Box
          className="instanceName"
          sx={{
            px: 4,
            py: 3,
            bgcolor: "primary.dark",
            color: "common.white",
            fontSize: "1.5rem",
            fontWeight: 700,
          }}
        >
          {instance.name}
        </Box>
        <Stack
          sx={{
            flexGrow: 1,
            justifyContent: "space-between",
            gap: 2,
            px: 4,
            py: 3,
          }}
        >
          {instance.description && (
            <Typography variant="body2" color="text.secondary">
              {instance.description}
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            {host(instance.url)}
          </Typography>
        </Stack>
      </Paper>
    ))}
  </Box>
);

export const PeopleGrid = ({ children }: { children: ReactNode }) => (
  <Box
    sx={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(9rem, 1fr))",
      gap: 3,
    }}
  >
    {children}
  </Box>
);

export const Person = ({
  avatar,
  name,
  detail,
}: {
  avatar: ReactNode;
  name: string;
  detail?: string | undefined;
}) => (
  <Stack sx={{ alignItems: "center", textAlign: "center", gap: 1 }}>
    {avatar}
    <Typography variant="body2">{name}</Typography>
    {detail && (
      <Typography variant="caption" color="text.secondary">
        {detail}
      </Typography>
    )}
  </Stack>
);

export interface TeamMember {
  name: string;
  image: string;
}

export const TeamGrid = ({ people }: { people: TeamMember[] }) => (
  <PeopleGrid>
    {people.map((person) => (
      <Person
        key={person.name}
        name={person.name}
        avatar={
          <Avatar
            alt=""
            src={person.image}
            sx={{ width: "5rem", height: "5rem" }}
          />
        }
      />
    ))}
  </PeopleGrid>
);

export interface Citation {
  title: string;
  authors: string;
  venue: string;
  url: string;
  reference: string;
  bibtex: string;
}

export const CitationBlocks = ({ citations }: { citations: Citation[] }) => {
  const dispatch = useAppDispatch();

  const copy = async (bibtex: string) => {
    await navigator.clipboard.writeText(bibtex);
    dispatch(showNotification("BibTeX copied"));
  };

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(15rem, 1fr))",
        gap: 2,
      }}
    >
      {citations.map((citation) => (
        <Paper
          key={citation.reference}
          variant="outlined"
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 0.5,
            p: 2.5,
            borderRadius: 2,
            borderLeft: 4,
            borderLeftColor: "primary.dark",
            bgcolor: (theme) => alpha(theme.palette.primary.main, 0.04),
          }}
        >
          <Link
            href={citation.url}
            underline="hover"
            sx={{ fontWeight: 700, lineHeight: 1.35, color: headingColor }}
          >
            {citation.title}
          </Link>
          <Typography variant="body2">{citation.authors}</Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ flexGrow: 1, fontStyle: "italic" }}
          >
            {citation.venue}
          </Typography>
          <Link href={citation.url} variant="caption" sx={{ mt: 1 }}>
            {citation.reference}
          </Link>
          <Button
            size="small"
            variant="outlined"
            onClick={() => copy(citation.bibtex)}
            sx={{ alignSelf: "flex-start", mt: 1, textTransform: "none" }}
          >
            Copy BibTeX
          </Button>
        </Paper>
      ))}
    </Box>
  );
};

export interface Funder {
  name: string;
  logo: string;
  url: string;
}

export const FunderLogos = ({ funders }: { funders: Funder[] }) => (
  <Stack
    direction="row"
    sx={{
      flexWrap: "wrap",
      justifyContent: "center",
      alignItems: "center",
      gap: "1.5rem 4rem",
      p: 2,
      borderRadius: 2,
      bgcolor: "common.white",
    }}
  >
    {funders.map((funder) => (
      <a key={funder.name} href={funder.url}>
        <Box
          component="img"
          src={funder.logo}
          alt={funder.name}
          sx={{
            display: "block",
            maxWidth: 180,
            height: "3.5rem",
            objectFit: "contain",
          }}
        />
      </a>
    ))}
  </Stack>
);

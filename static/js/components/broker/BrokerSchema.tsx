import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";

import { useGetBrokerAlertSchemaQuery } from "../../ducks/brokers";
import { useAppDispatch } from "../../types/hooks";
import Spinner from "../Spinner";
import { SchemaField, flattenSchema, noteOwner } from "./alertSchema";

const groupOf = (path: string) =>
  path.includes(".")
    ? (path.split(".")[0] ?? "").replace(/[[\]{}]+$/, "")
    : "alert";

const Highlight = ({ text, query }: { text: string; query: string }) => {
  const at = query ? text.toLowerCase().indexOf(query) : -1;
  if (at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <Box component="mark" sx={{ bgcolor: "warning.light", px: 0 }}>
        {text.slice(at, at + query.length)}
      </Box>
      {text.slice(at + query.length)}
    </>
  );
};

const Note = ({
  owner,
  note,
}: {
  owner?: string | undefined;
  note: string;
}) => (
  <Box
    sx={{
      px: 2,
      py: 0.75,
      borderTop: 1,
      borderColor: "divider",
    }}
  >
    {owner && (
      <Typography
        variant="caption"
        sx={{ fontFamily: "monospace", fontWeight: 600, mr: 1 }}
      >
        {owner}
      </Typography>
    )}
    <Typography variant="caption" color="text.secondary">
      {note}
    </Typography>
  </Box>
);

const BrokerSchema = ({
  brokerId,
  surveys,
}: {
  brokerId: number;
  surveys: string[];
}) => {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const survey = searchParams.get("survey") || surveys[0] || "";
  const search = searchParams.get("search") ?? "";
  const query = search.trim().toLowerCase();
  const target = decodeURIComponent(location.hash.slice(1));
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const {
    data: schema,
    isFetching,
    error,
  } = useGetBrokerAlertSchemaQuery({ brokerId, survey }, { skip: !survey });

  const { fields, notes } = useMemo(() => {
    const collected: Record<string, string> = {};
    const flat = schema ? flattenSchema(schema, "", {}, [], 0, collected) : [];
    return { fields: flat, notes: collected };
  }, [schema]);

  const groups = useMemo(() => {
    const byGroup = new Map<string, SchemaField[]>();
    fields.forEach((field) => {
      const owner = noteOwner(field.path, notes);
      const note = (owner && notes[owner]) || "";
      if (
        query &&
        !field.path.toLowerCase().includes(query) &&
        !note.toLowerCase().includes(query)
      ) {
        return;
      }
      const group = groupOf(field.path);
      byGroup.set(group, [...(byGroup.get(group) ?? []), field]);
    });
    return [...byGroup];
  }, [fields, notes, query]);

  const shown = groups.reduce((n, [, rows]) => n + rows.length, 0);

  const scrolledTo = useRef("");
  useEffect(() => {
    if (!target || fields.length === 0) return;
    setOpen((previous) => ({ ...previous, [groupOf(target)]: true }));
  }, [target, fields.length]);
  useEffect(() => {
    const row = target ? document.getElementById(target) : null;
    if (!row || scrolledTo.current === target) return;
    scrolledTo.current = target;
    row.scrollIntoView({ block: "center" });
  }, [target, open, fields.length]);

  const setParam = (key: string, value: string) =>
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );

  const copyLink = (path: string) => {
    const hash = `#${encodeURIComponent(path)}`;
    navigate({ search: location.search, hash }, { replace: true });
    navigator.clipboard
      ?.writeText(
        `${window.location.origin}${location.pathname}${location.search}${hash}`,
      )
      .then(() => dispatch(showNotification("Link copied")));
  };

  const isOpen = (group: string) => open[group] ?? Boolean(query);

  const noteOf = (path: string) => {
    const owner = noteOwner(path, notes);
    return owner ? (notes[owner] ?? "") : "";
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}
      >
        {surveys.length > 1 &&
          surveys.map((s) => (
            <Chip
              key={s}
              label={s}
              color={s === survey ? "primary" : "default"}
              variant={s === survey ? "filled" : "outlined"}
              onClick={() => {
                setParam("survey", s);
                setOpen({});
              }}
            />
          ))}
        <TextField
          size="small"
          placeholder="Search fields and notes"
          value={search}
          onChange={(e) => setParam("search", e.target.value)}
          sx={{ flex: 1, minWidth: 240, ml: surveys.length > 1 ? 1 : 0 }}
        />
        {fields.length > 0 && (
          <Typography variant="body2" color="text.secondary">
            {query
              ? `${shown} of ${fields.length} fields`
              : `${fields.length} fields`}
          </Typography>
        )}
      </Box>

      {isFetching && <Spinner />}
      {error && !isFetching && (
        <Alert severity="warning">
          {(error as any)?.data?.message || `No alert schema for ${survey}.`}
        </Alert>
      )}
      {!isFetching && !error && query && shown === 0 && (
        <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
          No field matches.
        </Typography>
      )}

      {!isFetching && groups.length > 0 && (
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          {groups.map(([group, rows], index) => (
            <Box key={group}>
              <ButtonBase
                onClick={() =>
                  setOpen((previous) => ({
                    ...previous,
                    [group]: !isOpen(group),
                  }))
                }
                sx={{
                  width: "100%",
                  justifyContent: "space-between",
                  px: 2,
                  py: 1,
                  bgcolor: "action.hover",
                  borderTop: index > 0 ? 1 : 0,
                  borderColor: "divider",
                }}
              >
                <Typography sx={{ fontFamily: "monospace", fontWeight: 600 }}>
                  {group}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {rows.length}
                </Typography>
              </ButtonBase>
              {isOpen(group) &&
                rows.map((field, i) => {
                  const owner = noteOwner(field.path, notes);
                  const note = noteOf(field.path);
                  const ownNote = owner === field.path.replace(/[[\]{}]+$/, "");
                  const startsRun =
                    Boolean(note) && note !== noteOf(rows[i - 1]?.path ?? "");
                  const inline =
                    startsRun &&
                    ownNote &&
                    note !== noteOf(rows[i + 1]?.path ?? "");
                  return (
                    <Fragment key={field.path}>
                      {startsRun && !inline && (
                        <Note
                          owner={ownNote ? undefined : (owner ?? undefined)}
                          note={note}
                        />
                      )}
                      <Box
                        id={field.path}
                        sx={{
                          display: "flex",
                          flexWrap: "wrap",
                          alignItems: "baseline",
                          columnGap: 2,
                          px: 2,
                          py: 0.5,
                          borderTop: 1,
                          borderColor: "divider",
                          bgcolor:
                            field.path === target
                              ? "action.selected"
                              : "transparent",
                        }}
                      >
                        <ButtonBase
                          onClick={() => copyLink(field.path)}
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.85rem",
                            textAlign: "left",
                            wordBreak: "break-all",
                            "&:hover": { textDecoration: "underline" },
                          }}
                        >
                          <Highlight text={field.path} query={query} />
                        </ButtonBase>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ fontFamily: "monospace", ml: "auto" }}
                        >
                          {field.type}
                        </Typography>
                        {inline && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ flexBasis: "100%" }}
                          >
                            {note}
                          </Typography>
                        )}
                      </Box>
                    </Fragment>
                  );
                })}
            </Box>
          ))}
        </Paper>
      )}
    </Box>
  );
};

export default BrokerSchema;

import { useMemo, useState } from "react";

import Box from "@mui/material/Box";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import type { Theme } from "@mui/material/styles";

import { AlertOption } from "../BrokerAlertCard";
import BrokerAlertFilters from "../BrokerAlertFilters";
import { AlertFilter, matchesFilters } from "../alertFields";
import { REAL_BOGUS, collectScores, scoreColor } from "./BoomMlScores";

const num = (d: number) => (v: unknown) =>
  typeof v === "number" ? v.toFixed(d) : "—";

const str = (v: unknown) => (v == null ? "—" : String(v));

interface Row {
  alert: AlertOption;
  raw: any;
  scores: Record<string, number>;
}

interface Column {
  label: string;
  // Raw value, so the column can be sorted and filtered on, not just displayed.
  value: (row: Row) => unknown;
  format: (v: unknown) => string;
  color?: (v: unknown) => string | undefined;
}

const COLUMNS = (survey: string): Column[] => {
  const isLSST = survey === "LSST";
  const isDECAM = survey === "DECAM";
  const hasProgramid = !isLSST && !isDECAM;
  return [
    {
      label: isLSST ? "diaSourceId" : "candid",
      value: ({ alert, raw }) =>
        raw?.diaSourceId ?? alert.candid ?? raw?.candid ?? raw?._id,
      format: str,
    },
    { label: "JD", value: ({ alert }) => alert.jd, format: num(5) },
    { label: "band", value: ({ raw }) => raw?.candidate?.band, format: str },
    {
      label: isDECAM ? "magap" : "magpsf",
      value: ({ alert }) => alert.magpsf,
      format: num(3),
    },
    {
      label: isDECAM ? "sigmagap" : "sigmapsf",
      value: ({ raw }) => raw?.candidate?.sigmapsf,
      format: num(3),
    },
    ...(isDECAM
      ? []
      : [
          {
            label: "isdiffpos",
            value: ({ raw }: Row) => raw?.candidate?.isdiffpos,
            format: str,
          },
        ]),
    {
      label: hasProgramid ? "drb" : "reliability",
      value: ({ raw }) =>
        hasProgramid ? raw?.candidate?.drb : raw?.candidate?.reliability,
      format: num(5),
    },
    {
      label: "snr",
      value: ({ raw }) => raw?.candidate?.snr_psf ?? raw?.candidate?.snr,
      format: num(2),
    },
    ...(hasProgramid
      ? [
          {
            label: "programid",
            value: ({ raw }: Row) => raw?.candidate?.programid,
            format: str,
          },
        ]
      : []),
  ];
};

// The ML scores shown as bubbles, repeated as columns so many alerts can be
// compared at once.
const scoreColumns = (rows: Row[], theme: Theme): Column[] => {
  const names: string[] = [];
  rows.forEach((r) =>
    Object.keys(r.scores).forEach((name) => {
      // Real/Bogus is already the drb/reliability column.
      if (name !== REAL_BOGUS && !names.includes(name)) names.push(name);
    }),
  );
  return names.map((name) => ({
    label: name,
    value: ({ scores }) => scores[name],
    format: (v) => (typeof v === "number" ? `${(v * 100).toFixed(0)}%` : "—"),
    color: (v) => (typeof v === "number" ? scoreColor(theme, v) : undefined),
  }));
};

interface BoomAlertMetadataProps {
  alerts: AlertOption[];
  survey: string;
  selectedCandid?: string | number | undefined;
  onSelect: (candid: string | number) => void;
}

const BoomAlertMetadata = ({
  alerts,
  survey,
  selectedCandid,
  onSelect,
}: BoomAlertMetadataProps) => {
  const theme = useTheme();
  const [filters, setFilters] = useState<AlertFilter[]>([]);
  const [orderBy, setOrderBy] = useState("JD");
  const [order, setOrder] = useState<"asc" | "desc">("desc");

  const rows: Row[] = useMemo(
    () =>
      alerts.map((alert) => ({
        alert,
        raw: alert.raw,
        scores: Object.fromEntries(
          collectScores(alert.raw).map((s) => [s.name, s.score]),
        ),
      })),
    [alerts],
  );

  const columns = useMemo(
    () => [...COLUMNS(survey), ...scoreColumns(rows, theme)],
    [rows, survey, theme],
  );

  const visible = useMemo(() => {
    const kept = filters.length
      ? rows.filter((r) =>
          matchesFilters(
            Object.fromEntries(columns.map((c) => [c.label, c.value(r)])),
            filters,
          ),
        )
      : rows;
    const col = columns.find((c) => c.label === orderBy);
    if (!col) return kept;
    const dir = order === "asc" ? 1 : -1;
    return [...kept].sort((a, b) => {
      const va = col.value(a);
      const vb = col.value(b);
      // Missing values last, whichever way the column is sorted.
      if (va == null || vb == null)
        return va == null ? (vb == null ? 0 : 1) : -1;
      if (typeof va === "number" && typeof vb === "number")
        return (va - vb) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  }, [rows, columns, filters, orderBy, order]);

  const onSort = (label: string) => {
    setOrder(orderBy === label && order === "asc" ? "desc" : "asc");
    setOrderBy(label);
  };

  return (
    <Box sx={{ mt: 1 }}>
      <BrokerAlertFilters
        label="Filter alerts"
        fields={columns.map((c) => c.label)}
        filters={filters}
        onChange={setFilters}
      />
      <Box sx={{ maxHeight: 200, overflow: "auto" }}>
        <Table
          size="small"
          stickyHeader
          sx={{ "& td, & th": { px: 0.75, fontSize: "0.7rem" } }}
        >
          <TableHead>
            <TableRow>
              {columns.map((c) => (
                <TableCell
                  key={c.label}
                  sortDirection={orderBy === c.label ? order : false}
                >
                  <TableSortLabel
                    active={orderBy === c.label}
                    direction={orderBy === c.label ? order : "asc"}
                    onClick={() => onSort(c.label)}
                  >
                    {c.label}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {visible.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length}>
                  <Typography variant="caption" color="text.secondary">
                    No alert matches the filters.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {visible.map((row) => (
              <TableRow
                key={String(row.alert.candid)}
                hover
                selected={row.alert.candid === selectedCandid}
                onClick={() => onSelect(row.alert.candid)}
                sx={{ cursor: "pointer" }}
              >
                {columns.map((c) => {
                  const v = c.value(row);
                  return (
                    <TableCell
                      key={c.label}
                      sx={{ backgroundColor: c.color?.(v) }}
                    >
                      {c.format(v)}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
};

export default BoomAlertMetadata;

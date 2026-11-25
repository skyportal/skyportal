import { useState } from "react";
import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { alpha } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useUpdateSourceMutation } from "../../ducks/source";
import { useGetUsersQuery } from "../../ducks/users";

export const REDSHIFT_TYPES = [
  { value: "spectroscopic", label: "Spectroscopic" },
  { value: "photometric", label: "Photometric" },
];

export const TYPE_LABELS: Record<string, string> = {
  spectroscopic: "spec-z",
  photometric: "photo-z",
};

const useStyles = makeStyles()((theme) => ({
  panel: {
    width: "22rem",
    padding: "1rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
  },
  title: {
    fontWeight: 600,
  },
  typeChoice: {
    display: "flex",
    gap: "0.5rem",
  },
  typeOption: {
    flex: 1,
    padding: "0.45rem 0.75rem",
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: 6,
    background: "transparent",
    color: theme.palette.text.secondary,
    font: "inherit",
    fontSize: "0.875rem",
    cursor: "pointer",
    "&:hover": {
      borderColor: theme.palette.text.secondary,
    },
  },
  typeSelected: {
    borderColor: theme.palette.primary.main,
    background: alpha(theme.palette.primary.main, 0.08),
    color: theme.palette.primary.main,
    fontWeight: 600,
    "&:hover": {
      borderColor: theme.palette.primary.main,
    },
  },
  actions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "0.5rem",
  },
  history: {
    borderTop: `1px solid ${theme.palette.divider}`,
    paddingTop: "0.75rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    maxHeight: "14rem",
    overflowY: "auto",
  },
  historyTitle: {
    fontSize: "0.75rem",
    fontWeight: 600,
    color: theme.palette.text.secondary,
    textTransform: "uppercase",
  },
  historyRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: "0.5rem",
    fontSize: "0.85rem",
  },
  historyMeta: {
    fontSize: "0.75rem",
    color: theme.palette.text.secondary,
    textAlign: "right",
  },
  historyUser: {
    color: theme.palette.primary.main,
    textDecoration: "none",
    "&:hover": {
      textDecoration: "underline",
    },
  },
}));

interface RedshiftHistoryItem {
  set_at_utc: string;
  set_by_user_id: number;
  value?: number | null;
  uncertainty?: number | null;
  origin?: string | null;
  type?: string | null;
}

interface SourceRedshiftProps {
  source: {
    id?: string;
    redshift?: number | null;
    redshift_error?: number | null;
    redshift_origin?: string | null;
    redshift_type?: string | null;
    redshift_history?: RedshiftHistoryItem[] | null;
    [key: string]: any;
  };
  readOnly?: boolean;
}

const zDigits = (zErr?: number | null) =>
  zErr ? Math.ceil(Math.abs(Math.log10(zErr))) : 4;

const formatZ = (z: number | string, zErr?: number | string | null) => {
  const err = zErr ? Number(zErr) : null;
  const digits = zDigits(err);
  return `${Number(z).toFixed(digits)}${
    err ? ` ± ${err.toFixed(digits)}` : ""
  }`;
};

const formState = (source: SourceRedshiftProps["source"]) => ({
  redshift: source.redshift != null ? String(source.redshift) : "",
  redshift_error:
    source.redshift_error != null ? String(source.redshift_error) : "",
  redshift_origin: source.redshift_origin ?? "",
  redshift_type: source.redshift_type ?? "",
});

const SourceRedshift = ({ source, readOnly = false }: SourceRedshiftProps) => {
  const { classes, cx } = useStyles();
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [state, setState] = useState(formState(source));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const allUsers =
    useGetUsersQuery({ slim: true }, { skip: !anchor }).data?.users ?? [];

  const history = [...(source.redshift_history ?? [])].reverse();
  const hasRedshift = source.redshift != null;
  const zValue = state.redshift.trim();
  const invalid = !zValue || isNaN(Number(zValue));

  if (readOnly && !hasRedshift && !history.length) {
    return <Chip size="small" variant="outlined" label="None" />;
  }

  const open = (e: React.MouseEvent<HTMLElement>) => {
    setState(formState(source));
    setAnchor(e.currentTarget);
  };

  const submit = async (payload: Record<string, any>) => {
    setIsSubmitting(true);
    const result = await updateSource({ id: source.id!, payload });
    setIsSubmitting(false);
    if ("error" in result) return;
    dispatch(showNotification("Source redshift successfully updated."));
    setAnchor(null);
  };

  const save = () =>
    submit({
      redshift: zValue,
      redshift_error: state.redshift_error.trim() || null,
      redshift_origin: state.redshift_origin.trim() || null,
      redshift_type: state.redshift_type || null,
    });

  const clear = () =>
    submit({
      redshift: null,
      redshift_error: null,
      redshift_origin: null,
      redshift_type: null,
    });

  const setField = (e: React.ChangeEvent<HTMLInputElement>) =>
    setState({ ...state, [e.target.name]: e.target.value });

  const typeLabel = source.redshift_type
    ? TYPE_LABELS[source.redshift_type]
    : null;

  return (
    <>
      <Chip
        size="small"
        data-testid="redshiftChip"
        variant={hasRedshift ? "filled" : "outlined"}
        label={
          hasRedshift
            ? [formatZ(source.redshift!, source.redshift_error), typeLabel]
                .filter(Boolean)
                .join(" · ")
            : "None"
        }
        onClick={open}
      />
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <div className={classes.panel}>
          <div className={classes.title}>Redshift</div>
          {!readOnly && (
            <>
              <TextField
                data-testid="updateRedshiftTextfield"
                size="small"
                label="z"
                name="redshift"
                value={state.redshift}
                onChange={setField}
                error={Boolean(zValue) && invalid}
                autoFocus
                fullWidth
              />
              <TextField
                data-testid="updateRedshiftErrorTextfield"
                size="small"
                label="z_err"
                name="redshift_error"
                value={state.redshift_error}
                onChange={setField}
                fullWidth
              />
              <TextField
                data-testid="updateRedshiftOriginTextfield"
                size="small"
                label="Origin (optional)"
                name="redshift_origin"
                value={state.redshift_origin}
                onChange={setField}
                fullWidth
              />
              <div className={classes.typeChoice}>
                {REDSHIFT_TYPES.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    data-testid={`redshiftType_${value}`}
                    className={cx(
                      classes.typeOption,
                      state.redshift_type === value && classes.typeSelected,
                    )}
                    onClick={() => setState({ ...state, redshift_type: value })}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className={classes.actions}>
                {hasRedshift && (
                  <Tooltip title="Remove the redshift from this source">
                    <span>
                      <Button
                        secondary
                        size="small"
                        onClick={clear}
                        disabled={isSubmitting}
                        data-testid="nullifyRedshiftButton"
                      >
                        Clear
                      </Button>
                    </span>
                  </Tooltip>
                )}
                <Button
                  primary
                  size="small"
                  onClick={save}
                  disabled={isSubmitting || invalid || !state.redshift_type}
                  data-testid="updateRedshiftSubmitButton"
                >
                  Save
                </Button>
              </div>
            </>
          )}
          {history.length > 0 && (
            <div className={classes.history} data-testid="redshiftHistory">
              <div className={classes.historyTitle}>History</div>
              {history.map((entry) => (
                <div
                  key={`${entry.set_at_utc}-${entry.set_by_user_id}`}
                  className={classes.historyRow}
                >
                  <div>
                    <div>
                      {entry.value != null
                        ? formatZ(entry.value, entry.uncertainty)
                        : "Cleared"}
                    </div>
                    <div className={classes.historyMeta}>
                      {[
                        entry.type ? TYPE_LABELS[entry.type] : null,
                        entry.origin,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                  <div className={classes.historyMeta}>
                    <Link
                      to={`/user/${entry.set_by_user_id}`}
                      className={classes.historyUser}
                    >
                      {allUsers.find((u: any) => u.id === entry.set_by_user_id)
                        ?.username ?? entry.set_by_user_id}
                    </Link>
                    <div>
                      {`${entry.set_at_utc.slice(0, 16).replace("T", " ")} UTC`}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Popover>
    </>
  );
};

export default SourceRedshift;

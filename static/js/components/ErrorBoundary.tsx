import React from "react";
import { connect } from "react-redux";

import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import type { RootState } from "../types/store";
import { POST } from "../API";
import { sysInfoApi } from "../ducks/sysInfo";

dayjs.extend(utc);

const LOG_ERROR = "skyportal/LOG_ERROR";
const logError = (errorInfo: any) =>
  POST(`/api/internal/log`, LOG_ERROR, errorInfo);

interface ErrorBoundaryProps {
  dispatch: (action: any) => void;
  version?: string | null;
  children?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: any;
  stack: string | null;
  errorTime: string | null;
  displayStack: boolean;
}

class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  static defaultProps: any = {
    version: null,
    children: [],
  };

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      stack: null,
      errorTime: null,
      displayStack: false,
    };
  }

  static getDerivedStateFromError(error: any) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error, errorTime: dayjs.utc().format() };
  }

  override componentDidCatch(error: any, errorInfo: any) {
    // You can also log the error to an error reporting service
    const { dispatch } = this.props;
    this.setState({
      stack: errorInfo.componentStack,
    });
    dispatch(
      logError({
        error: error.toString(),
        stack: errorInfo.componentStack,
      }),
    );
  }

  errorReport(returnStack: boolean) {
    const { error, stack, errorTime } = this.state;
    const { version } = this.props;
    return [
      `${errorTime} - This is SkyPortal ${version || "N/A"}`,
      error && error.toString(),
      returnStack && stack,
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  override render() {
    const { hasError, stack, displayStack } = this.state;
    const { children } = this.props;
    if (hasError) {
      return (
        <div
          style={{
            padding: "clamp(1rem, 5vw, 5rem)",
            width: "min(90%, 1000px)",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          <div style={{ textAlign: "center", paddingBottom: "1rem" }}>
            <img
              src="/static/images/something_wrong.svg"
              style={{ maxWidth: "250px", width: "80%" }}
              alt="Something went wrong"
            />
            <h1>Oh dear! Something went wrong.</h1>
          </div>

          <p>
            We logged the error and will take a look. Please let us know if this
            issue is preventing you from doing your work.
            <br />
            If you want to help us debug the issue, please send us the
            information below or{" "}
            <a
              href="https://github.com/skyportal/skyportal/issues"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#1976d2" }}
            >
              open an issue on GitHub
            </a>
            .
          </p>

          <pre
            style={{
              border: "solid lightgray 1px",
              background: "#eee",
              padding: "1rem",
              paddingRight: "2rem",
              borderRadius: "0.5rem",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              position: "relative",
            }}
          >
            <Tooltip title="Copy to clipboard">
              <IconButton
                sx={{ position: "absolute", top: "0.5rem", right: "0.5rem" }}
                size="small"
                onClick={() =>
                  navigator.clipboard.writeText(this.errorReport(true))
                }
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            {this.errorReport(displayStack)}
          </pre>
          {stack && (
            <Button
              size="small"
              sx={{ display: "block", ml: "auto", mb: "0.5rem" }}
              onClick={() => this.setState({ displayStack: !displayStack })}
            >
              {displayStack ? "Hide stack" : "Show stack"}
            </Button>
          )}
        </div>
      );
    }

    return children;
  }
}

const mapStateToProps = (state: RootState) => ({
  // Best-effort: reads the version from the RTK Query cache if `getSysInfo` has
  // been fetched (it is, during app hydration). `select()` with no arg targets
  // the `void`-arg query.
  version: sysInfoApi.endpoints.getSysInfo.select()(state)?.data?.version,
});

export default connect(mapStateToProps)(ErrorBoundary);

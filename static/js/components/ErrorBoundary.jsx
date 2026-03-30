import React from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { POST } from "../API";

dayjs.extend(utc);

const LOG_ERROR = "skyportal/LOG_ERROR";
const logError = (errorInfo) => POST(`/api/internal/log`, LOG_ERROR, errorInfo);

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    const { dispatch } = this.props;
    dispatch(
      logError({
        error: error.toString(),
        stack: errorInfo.componentStack,
      }),
    );
  }

  render() {
    const { hasError, error } = this.state;
    const { version, children } = this.props;
    if (hasError) {
      return (
        <div
          style={{
            padding: "clamp(1em, 5vw, 5em)",
            width: "min(90%, 1000px)",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          <div style={{ textAlign: "center", paddingBottom: "1em" }}>
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
              padding: "1em",
              borderRadius: "0.5em",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {dayjs.utc().format()} - This is SkyPortal {version || "N/A"}
            {error && (
              <>
                <br />
                <br />
                {error.toString()}
              </>
            )}
          </pre>
        </div>
      );
    }

    return children;
  }
}
ErrorBoundary.propTypes = {
  dispatch: PropTypes.func.isRequired,
  version: PropTypes.string,
  children: PropTypes.oneOfType([
    PropTypes.node,
    PropTypes.arrayOf(PropTypes.node),
  ]),
};
ErrorBoundary.defaultProps = {
  version: null,
  children: [],
};

const mapStateToProps = (state) => ({
  version: state.sysInfo?.version,
});

export default connect(mapStateToProps)(ErrorBoundary);

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
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
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
    const { hasError } = this.state;
    const { version, children } = this.props;
    if (hasError) {
      return (
        <div
          style={{
            padding: "5em",
            width: "50%",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          <div style={{ textAlign: "center", paddingBottom: "1em" }}>
            <img
              src="/static/images/car_over_cliff.svg"
              width="300em"
              style={{ textAlign: "center" }}
              alt="Car over cliff: something went wrong"
            />
            <h1>Oh dear! Something went wrong.</h1>
          </div>

          <p>
            We logged the error and will take a look. Please let us know if this
            issue is preventing you from doing your work.
          </p>

          <p>
            If you want to help us debug the issue, please send us the following
            debugging information:
          </p>

          <pre
            style={{
              border: "solid lightgray 1px",
              background: "#eee",
              padding: "1em",
              borderRadius: "0.5em",
            }}
          >
            An error occurred at {dayjs.utc().format()}(
            {dayjs().utcOffset(-7).format("HH:mm:ss")} PST).
            {version && (
              <>
                <br />
                This is SkyPortal {version}.
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

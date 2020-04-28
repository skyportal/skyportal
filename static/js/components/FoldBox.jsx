import React, { Component } from "react";
import PropTypes from "prop-types";

class FoldBox extends Component {
  constructor(props) {
    super(props);
    const { folded } = this.props;
    this.state = { folded };
    this.toggleFold = this.toggleFold.bind(this);
  }

  toggleFold() {
    const { folded } = this.state;
    this.setState({ folded: !folded });
  }

  render() {
    const { folded } = this.state;
    const { children, title } = this.props;
    const folded_children = folded ? null : children;

    const onClick = (e) => {
      e.stopPropagation();
      this.toggleFold();
    };

    return (
      <div style={{ paddingTop: "0.25em", outline: "none" }}>
        <div
          onClick={onClick}
          onKeyDown={onClick}
          role="button"
          tabIndex={0}
          style={{ fontSize: "150%" }}
        >
          {folded ? "▸" : "▾"}
          {title}
        </div>
        {folded_children}
      </div>
    );
  }
}
FoldBox.propTypes = {
  folded: PropTypes.bool,
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
};
FoldBox.defaultProps = {
  folded: false,
  children: null,
};

export default FoldBox;

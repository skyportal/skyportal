import React, { Component } from 'react';
import PropTypes from 'prop-types';


class FoldBox extends Component {
  constructor(props) {
    super(props);
    this.state = { folded: this.props.folded };
    this.toggleFold = this.toggleFold.bind(this);
  }

  toggleFold() {
    const folded = !this.state.folded;
    this.setState({ folded });
  }

  render() {
    const children = this.state.folded ? null : this.props.children;
    const onClick = (e) => {
      e.stopPropagation();
      this.toggleFold();
    };

    return (
      <div
        style={{ paddingTop: '0.25em', outline: 'none' }}
      >
        <div
          onClick={onClick}
          onKeyDown={onClick}
          role="button"
          tabIndex={0}
          style={{ fontSize: '150%' }}
        >
          {this.state.folded ? '▸' : '▾'}
          {' '}
          {this.props.title}
        </div>
        {children}
      </div>
    );
  }
}
FoldBox.propTypes = {
  folded: PropTypes.bool,
  title: PropTypes.string.isRequired,
  children: PropTypes.node
};
FoldBox.defaultProps = {
  folded: false,
  children: null
};

export default FoldBox;

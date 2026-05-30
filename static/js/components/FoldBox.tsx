import React, { Component } from "react";

interface FoldBoxProps {
  folded?: boolean;
  title: string;
  children?: React.ReactNode;
}

interface FoldBoxState {
  folded: boolean;
}

class FoldBox extends Component<FoldBoxProps, FoldBoxState> {
  static defaultProps: any = {
    folded: false,
    children: null,
  };

  constructor(props: FoldBoxProps) {
    super(props);
    const { folded } = this.props;
    this.state = { folded: !!folded };
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

    const onClick = (e: any) => {
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
          {folded ? "▸" : "▾"} {title}
        </div>
        {folded_children}
      </div>
    );
  }
}

export default FoldBox;

/* eslint-disable max-classes-per-file, import/no-extraneous-dependencies */

import { input, label, div, span } from "bokehjs/core/dom";
import { includes } from "bokehjs/core/util/array";
import * as p from "bokehjs/core/properties";
import { bk_inline } from "bokehjs/styles/mixins";
import { bk_input_group } from "bokehjs/styles/widgets/inputs";
import {
  CheckboxGroup,
  CheckboxGroupView,
} from "bokehjs/models/widgets/checkbox_group";
import { InputGroupView } from "bokehjs/models/widgets/input_group";

export class CheckboxWithLegendGroupView extends CheckboxGroupView {
  render() {
    InputGroupView.prototype.render.call(this);
    const group = div({
      class: [bk_input_group, this.model.inline ? bk_inline : null],
    });
    this.el.appendChild(group);
    const { active, colors, labels } = this.model;
    // eslint-disable-next-line no-underscore-dangle
    this._inputs = [];
    for (let i = 0; i < labels.length; i += 1) {
      const checkbox = input({ type: "checkbox", value: `${i}` });
      checkbox.addEventListener("change", () => this.change_active(i));
      // eslint-disable-next-line no-underscore-dangle
      this._inputs.push(checkbox);
      if (this.model.disabled) checkbox.disabled = true;
      if (includes(active, i)) checkbox.checked = true;
      const attrs = {
        style: `border-left: 12px solid ${colors[i]}; padding-left: 0.3em;`,
      };
      const label_el = label(attrs, checkbox, span({}, labels[i]));
      group.appendChild(label_el);
    }
  }

  change_active(i) {
    const active = new Set(this.model.active);
    if (active.has(i)) {
      active.delete(i);
    } else {
      active.add(i);
    }
    this.model.active = [...active].sort();
  }
}
// eslint-disable-next-line no-underscore-dangle
CheckboxWithLegendGroupView.__name__ = "CheckboxWithLegendGroupView";

export class CheckboxWithLegendGroup extends CheckboxGroup {
  static init_CheckboxWithLegendGroup() {
    this.prototype.default_view = CheckboxWithLegendGroupView;
    this.define({
      colors: [p.Array, []],
    });
  }
}
// eslint-disable-next-line no-underscore-dangle
CheckboxWithLegendGroup.__name__ = "CheckboxWithLegendGroup";
CheckboxWithLegendGroup.init_CheckboxWithLegendGroup();

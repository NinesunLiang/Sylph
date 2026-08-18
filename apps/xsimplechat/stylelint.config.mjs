export default {
  extends: ["stylelint-config-standard-scss"],
  rules: {
    "scss/dollar-variable-pattern": null,
    "scss/at-rule-no-unknown": [
      true,
      { ignoreAtRules: ["use", "forward", "mixin", "include", "function", "return", "each"] },
    ],
    "no-descending-specificity": null,
    "selector-class-pattern": null,
  },
};

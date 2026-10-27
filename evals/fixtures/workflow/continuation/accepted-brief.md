# Accepted maintenance contract

Keep `category_summary(count)` unchanged as the public interface for
nonnegative integer counts. Exact required results:

- 0: `No suspicious categories detected.`
- 1: `1 suspicious category detected.`
- 2: `2 suspicious categories detected.`
- Any count greater than 1 uses `categories` and the supplied count.

Do not change PRODUCT_LABEL, add validation for new input domains, change
punctuation, introduce dependencies or refactor unrelated code. Local code
and regression-test changes are approved. External publication is not.

import "@testing-library/jest-dom/vitest";
import { toHaveNoViolations } from "jest-axe";
import { expect } from "vitest";

expect.extend(toHaveNoViolations);

declare module "vitest" {
  interface Assertion<T> {
    toHaveNoViolations(): T;
  }
}

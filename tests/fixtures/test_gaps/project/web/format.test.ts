import { test, expect } from "vitest";
import { formatDate } from "./format";

test("formatDate", () => {
  expect(formatDate(new Date("2026-01-02T00:00:00Z"))).toBe("2026-01-02");
});

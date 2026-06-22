import "@testing-library/jest-dom";
import { server } from "./mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// JSDOM no implementa scrollIntoView — mock global
Element.prototype.scrollIntoView = vi.fn();

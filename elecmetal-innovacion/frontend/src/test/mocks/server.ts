// @ts-nocheck — msw/node types disponibles tras npm install
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);

import assert from "node:assert/strict";
import test from "node:test";

import { FinalTextState, ProbeProtocolError, ToolCallState } from "../../scripts/responses_stream_state.mjs";

const INITIAL_EVENTS = [
  { type: "response.created", response: { id: "resp_initial" } },
  {
    type: "response.output_item.added",
    item: { type: "function_call", id: "item_status", call_id: "call_status", name: "status" },
  },
  { type: "response.function_call_arguments.delta", item_id: "item_status", delta: "{" },
  { type: "response.function_call_arguments.delta", item_id: "item_status", delta: "}" },
  {
    type: "response.function_call_arguments.done",
    item_id: "item_status",
    name: "status",
    arguments: "{}",
  },
  {
    type: "response.output_item.done",
    item: {
      type: "function_call",
      id: "item_status",
      call_id: "call_status",
      name: "status",
      arguments: "{}",
    },
  },
  { type: "response.completed", response: { id: "resp_initial" } },
];

test("decodes one linked streamed status tool call", () => {
  const state = new ToolCallState();
  for (const event of INITIAL_EVENTS) state.accept(event);
  assert.deepEqual(state.finish(), {
    responseId: "resp_initial",
    itemId: "item_status",
    callId: "call_status",
    name: "status",
    arguments: "{}",
  });
});

test("accepts omitted done-event name but rejects a contradictory name", () => {
  const withoutOptionalName = INITIAL_EVENTS.map((event) => ({ ...event }));
  delete withoutOptionalName[4].name;
  const accepted = new ToolCallState();
  for (const event of withoutOptionalName) accepted.accept(event);
  assert.equal(accepted.finish().name, "status");

  const contradicted = new ToolCallState();
  contradicted.accept(INITIAL_EVENTS[0]);
  contradicted.accept(INITIAL_EVENTS[1]);
  assert.throws(
    () =>
      contradicted.accept({
        type: "response.function_call_arguments.done",
        item_id: "item_status",
        name: "other",
        arguments: "{}",
      }),
    (error) => error instanceof ProbeProtocolError && error.code === "TOOL_NAME_CHANGED",
  );
});

test("rejects changed call identity and malformed tool arguments", () => {
  const changed = new ToolCallState();
  changed.accept(INITIAL_EVENTS[0]);
  changed.accept(INITIAL_EVENTS[1]);
  assert.throws(
    () =>
      changed.accept({
        type: "response.output_item.done",
        item: {
          type: "function_call",
          id: "item_status",
          call_id: "call_other",
          name: "status",
          arguments: "{}",
        },
      }),
    (error) => error instanceof ProbeProtocolError && error.code === "TOOL_CALL_ID_CHANGED",
  );

  const malformed = new ToolCallState();
  for (const event of [
    INITIAL_EVENTS[0],
    INITIAL_EVENTS[1],
    {
      type: "response.function_call_arguments.done",
      item_id: "item_status",
      name: "status",
      arguments: '{"unexpected":true}',
    },
    INITIAL_EVENTS.at(-1),
  ]) {
    malformed.accept(event);
  }
  assert.throws(
    () => malformed.finish(),
    (error) => error instanceof ProbeProtocolError && error.code === "TOOL_ARGUMENTS_INVALID",
  );
});

test("requires a completed continued final text response", () => {
  const state = new FinalTextState();
  for (const event of [
    { type: "response.created", response: { id: "resp_final" } },
    { type: "response.output_text.delta", delta: "Probe " },
    { type: "response.output_text.delta", delta: "complete." },
    { type: "response.output_text.done", text: "Probe complete." },
    { type: "response.completed", response: { id: "resp_final" } },
  ]) {
    state.accept(event);
  }
  assert.deepEqual(state.finish(), { responseId: "resp_final", text: "Probe complete." });
});

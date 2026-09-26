export class ProbeProtocolError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

function requireEqual(observed, expected, code) {
  if (observed !== undefined && observed !== expected) {
    throw new ProbeProtocolError(code);
  }
}

export class ToolCallState {
  constructor() {
    this.itemId = undefined;
    this.callId = undefined;
    this.name = undefined;
    this.arguments = "";
    this.doneArguments = undefined;
    this.responseId = undefined;
    this.completed = false;
  }

  adopt(item) {
    if (!item || item.type !== "function_call") return;
    if (this.itemId !== undefined && item.id !== this.itemId) {
      throw new ProbeProtocolError("MULTIPLE_TOOL_CALLS");
    }
    requireEqual(this.callId, item.call_id, "TOOL_CALL_ID_CHANGED");
    requireEqual(this.name, item.name, "TOOL_NAME_CHANGED");
    this.itemId = item.id;
    this.callId = item.call_id;
    this.name = item.name;
    if (typeof item.arguments === "string" && item.arguments.length > 0) {
      if (this.arguments.length > 0 && this.arguments !== item.arguments) {
        throw new ProbeProtocolError("TOOL_ARGUMENTS_CHANGED");
      }
      this.doneArguments = item.arguments;
    }
  }

  accept(event) {
    if (!event || typeof event.type !== "string") {
      throw new ProbeProtocolError("INVALID_STREAM_EVENT");
    }
    if (event.type === "response.created") {
      requireEqual(this.responseId, event.response?.id, "RESPONSE_ID_CHANGED");
      this.responseId = event.response?.id;
    } else if (event.type === "response.output_item.added") {
      this.adopt(event.item);
    } else if (event.type === "response.function_call_arguments.delta") {
      if (event.item_id !== this.itemId || typeof event.delta !== "string") {
        throw new ProbeProtocolError("TOOL_ARGUMENT_DELTA_UNLINKED");
      }
      this.arguments += event.delta;
    } else if (event.type === "response.function_call_arguments.done") {
      if (event.item_id !== this.itemId || typeof event.arguments !== "string") {
        throw new ProbeProtocolError("TOOL_ARGUMENT_DONE_UNLINKED");
      }
      requireEqual(this.name, event.name, "TOOL_NAME_CHANGED");
      if (this.arguments.length > 0 && this.arguments !== event.arguments) {
        throw new ProbeProtocolError("TOOL_ARGUMENTS_CHANGED");
      }
      this.doneArguments = event.arguments;
    } else if (event.type === "response.output_item.done") {
      this.adopt(event.item);
    } else if (event.type === "response.completed") {
      requireEqual(this.responseId, event.response?.id, "RESPONSE_ID_CHANGED");
      this.responseId = event.response?.id;
      this.completed = true;
    } else if (event.type === "error" || event.type === "response.failed") {
      throw new ProbeProtocolError("PROVIDER_STREAM_FAILED");
    }
  }

  finish() {
    if (!this.completed || !this.responseId) {
      throw new ProbeProtocolError("INITIAL_RESPONSE_INCOMPLETE");
    }
    if (!this.itemId || !this.callId || this.name !== "status") {
      throw new ProbeProtocolError("STATUS_TOOL_CALL_MISSING");
    }
    const encoded = this.doneArguments ?? this.arguments;
    let decoded;
    try {
      decoded = JSON.parse(encoded);
    } catch {
      throw new ProbeProtocolError("TOOL_ARGUMENTS_INVALID");
    }
    if (
      decoded === null ||
      Array.isArray(decoded) ||
      typeof decoded !== "object" ||
      Object.keys(decoded).length !== 0
    ) {
      throw new ProbeProtocolError("TOOL_ARGUMENTS_INVALID");
    }
    return {
      responseId: this.responseId,
      itemId: this.itemId,
      callId: this.callId,
      name: this.name,
      arguments: encoded,
    };
  }
}

export class FinalTextState {
  constructor() {
    this.responseId = undefined;
    this.text = "";
    this.doneText = undefined;
    this.completed = false;
  }

  accept(event) {
    if (!event || typeof event.type !== "string") {
      throw new ProbeProtocolError("INVALID_STREAM_EVENT");
    }
    if (event.type === "response.created") {
      requireEqual(this.responseId, event.response?.id, "RESPONSE_ID_CHANGED");
      this.responseId = event.response?.id;
    } else if (event.type === "response.output_text.delta") {
      if (typeof event.delta !== "string") {
        throw new ProbeProtocolError("FINAL_TEXT_INVALID");
      }
      this.text += event.delta;
    } else if (event.type === "response.output_text.done") {
      if (typeof event.text !== "string") {
        throw new ProbeProtocolError("FINAL_TEXT_INVALID");
      }
      if (this.text.length > 0 && this.text !== event.text) {
        throw new ProbeProtocolError("FINAL_TEXT_CHANGED");
      }
      this.doneText = event.text;
    } else if (
      event.type === "response.output_item.added" &&
      event.item?.type === "function_call"
    ) {
      throw new ProbeProtocolError("UNEXPECTED_SECOND_TOOL_CALL");
    } else if (event.type === "response.completed") {
      requireEqual(this.responseId, event.response?.id, "RESPONSE_ID_CHANGED");
      this.responseId = event.response?.id;
      this.completed = true;
    } else if (event.type === "error" || event.type === "response.failed") {
      throw new ProbeProtocolError("PROVIDER_STREAM_FAILED");
    }
  }

  finish() {
    const text = this.doneText ?? this.text;
    if (!this.completed || !this.responseId || text.trim().length === 0) {
      throw new ProbeProtocolError("FINAL_RESPONSE_INCOMPLETE");
    }
    return { responseId: this.responseId, text };
  }
}
